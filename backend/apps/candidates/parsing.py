from __future__ import annotations

import io
import re
import threading
from typing import Dict, List, Optional, Tuple

import phonenumbers
from django.conf import settings
from django.utils import timezone
from pypdf import PdfReader
from docx import Document as DocxDocument

from .models import Candidate, Resume, Extraction


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# token-ish skills; tune to your interests
SKILL_TOKENS = {
    "python", "django", "flask", "react", "javascript", "typescript",
    "postgres", "postgresql", "sqlite", "redis", "docker", "kubernetes",
    "aws", "gcp", "azure", "celery", "langchain", "pytorch", "tensorflow",
    "nlp", "llm", "openai", "anthropic", "gpt", "fastapi",
}

DESIGNATION_HINTS = [
    "software engineer", "senior software", "sde", "developer",
    "data scientist", "machine learning", "ml engineer",
    "frontend", "backend", "full stack", "tech lead", "engineering manager",
]

COMPANY_HINTS = [" at ", " @ ", "experience", "work history", "employment"]


def queue_parse_resume(resume_id: int) -> None:
    """Spawn a daemon thread to parse a resume by id."""
    t = threading.Thread(target=parse_resume, args=(resume_id,), daemon=True)
    t.start()


def parse_resume(resume_id: int) -> None:
    resume = Resume.objects.select_related("candidate").get(id=resume_id)
    candidate = resume.candidate

    extraction = Extraction.objects.create(
        candidate=candidate,
        resume=resume,
        status=Extraction.Status.STARTED,
        model_name="heuristics",
    )

    try:
        # Extract plain text
        text = extract_text_from_file(resume)
        # Heuristics
        fields, conf = extract_fields_heuristics(text)
        # Optional LLM enhancement
        if getattr(settings, "USE_LLM", False):
            llm_fields, llm_conf, llm_model = try_llm_extract(text)
            if llm_fields:
                fields.update({k: v for k, v in llm_fields.items() if v})
                for k, v in llm_conf.items():
                    conf[k] = max(conf.get(k, 0.0), v)
                extraction.model_name = llm_model or "heuristics+llm"

        # Update candidate
        candidate.name = fields.get("name", candidate.name or "")
        candidate.primary_email = fields.get("email", candidate.primary_email or "")
        candidate.primary_phone = fields.get("phone", candidate.primary_phone or "")
        candidate.latest_company = fields.get("company", candidate.latest_company or "")
        candidate.designation = fields.get("designation", candidate.designation or "")
        candidate.extraction_status = Candidate.ExtractionStatus.PARSED
        candidate.save(update_fields=[
            "name", "primary_email", "primary_phone", "latest_company",
            "designation", "extraction_status", "updated_at",
        ])

        # Persist extraction
        extraction.raw_text = text[:300000]  # avoid huge blobs
        extraction.fields_json = fields
        extraction.confidences_json = conf
        extraction.status = Extraction.Status.COMPLETED
        extraction.completed_at = timezone.now()
        extraction.save(update_fields=[
            "raw_text", "fields_json", "confidences_json", "status", "completed_at"
        ])

        resume.status = Resume.Status.PARSED
        resume.save(update_fields=["status"])

    except Exception as e:  # noqa: BLE001
        candidate.extraction_status = Candidate.ExtractionStatus.FAILED
        candidate.save(update_fields=["extraction_status", "updated_at"])
        extraction.status = Extraction.Status.FAILED
        extraction.save(update_fields=["status"])
        resume.status = Resume.Status.FAILED
        resume.save(update_fields=["status"])
        # For a personal project, noisy errors help.
        import traceback
        traceback.print_exc()


def extract_text_from_file(resume: Resume) -> str:
    name = (resume.original_name or "").lower()
    with resume.file.open("rb") as fh:
        data = fh.read()
    if name.endswith(".pdf") or (resume.mime_type or "").startswith("application/pdf"):
        return extract_text_from_pdf(io.BytesIO(data))
    if name.endswith(".docx") or "officedocument.wordprocessingml.document" in (resume.mime_type or ""):
        return extract_text_from_docx(io.BytesIO(data))
    # fallback: try pdf first, then docx
    try:
        return extract_text_from_pdf(io.BytesIO(data))
    except Exception:
        return extract_text_from_docx(io.BytesIO(data))


def extract_text_from_pdf(buf: io.BytesIO) -> str:
    reader = PdfReader(buf)
    chunks: List[str] = []
    for page in reader.pages:
        try:
            chunks.append(page.extract_text() or "")
        except Exception:
            # ignore bad page; keep going
            continue
    return "\n".join(chunks)


def extract_text_from_docx(buf: io.BytesIO) -> str:
    doc = DocxDocument(buf)
    return "\n".join(p.text for p in doc.paragraphs)


def extract_fields_heuristics(text: str) -> Tuple[Dict[str, str], Dict[str, float]]:
    t = text or ""
    t_norm = t.replace("\r", "")
    lines = [ln.strip() for ln in t_norm.split("\n") if ln.strip()]
    lower = t_norm.lower()

    fields: Dict[str, str] = {}
    conf: Dict[str, float] = {}

    # Name guess: first non-empty line with 2-5 words, mostly alphabetic.
    name = ""
    for ln in lines[:10]:
        words = [w for w in re.split(r"\s+", ln) if w]
        if 2 <= len(words) <= 5 and sum(ch.isalpha() for ch in ln) / max(1, len(ln)) > 0.7:
            name = ln
            break
    if name:
        fields["name"] = name
        conf["name"] = 0.6

    # Email(s)
    emails = EMAIL_RE.findall(t)
    if emails:
        fields["email"] = emails[0]
        conf["email"] = 0.95

    # Phone(s) – prefer Indian numbers (+91 or 10 digits)
    phone_val = ""
    try:
        for match in phonenumbers.PhoneNumberMatcher(t, "IN"):
            num = phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.E164)
            if num:
                phone_val = num
                break
    except Exception:
        pass
    if not phone_val:
        # crude 10-digit fallback
        digits = re.findall(r"(?:\+91[-\s]?)?\b[6-9]\d{9}\b", t)
        if digits:
            d = digits[0].replace(" ", "").replace("-", "")
            if not d.startswith("+"):
                d = "+91" + d[-10:]
            phone_val = d
    if phone_val:
        fields["phone"] = phone_val
        conf["phone"] = 0.9

    # Company guess: look for " at X" or under Experience sections
    company = ""
    for hint in COMPANY_HINTS:
        idx = lower.find(hint)
        if idx != -1:
            seg = t_norm[idx: idx + 120]
            # Take the token after " at " or " @ "
            m = re.search(r"(?:\bat\b|\s@\s)([A-Z][A-Za-z0-9& ._-]{2,})", seg)
            if m:
                company = m.group(1).strip().split("  ")[0]
                break
    if not company:
        # fallback: next line after "Experience"
        for i, ln in enumerate(lines):
            if ln.lower().startswith("experience"):
                company = lines[i + 1] if i + 1 < len(lines) else ""
                break
    if company:
        fields["company"] = company
        conf["company"] = 0.55

    # Designation guess
    designation = ""
    for ln in lines[:30]:
        lnl = ln.lower()
        if any(h in lnl for h in DESIGNATION_HINTS):
            designation = ln
            break
    if designation:
        fields["designation"] = designation
        conf["designation"] = 0.6

    # Skills based on token inclusion
    skills_found: List[str] = []
    lower_tokens = set(re.findall(r"[a-zA-Z+#.]+", lower))
    for sk in SKILL_TOKENS:
        if sk in lower_tokens:
            skills_found.append(sk if sk != "postgres" else "postgresql")
    if skills_found:
        fields["skills"] = sorted(set(skills_found))
        conf["skills"] = {sk: 0.85 for sk in fields["skills"]}

    return fields, conf


def try_llm_extract(text: str) -> Tuple[Optional[Dict[str, str]], Dict[str, float], Optional[str]]:
    """
    Optional: if USE_LLM=true and OpenAI client available, ask the model to return a JSON object.
    Returns (fields, confidences, model_name). On failure, returns (None, {}, None).
    """
    if not getattr(settings, "USE_LLM", False):
        return None, {}, None

    import json
    from openai import OpenAI

    client = OpenAI(api_key=getattr(settings, "OPENAI_API_KEY", ""))
    model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

    # Trim text so you don’t pay to send megabytes
    snippet = text[:12000]

    system = (
        "You extract resume fields for an HR pipeline. "
        "Return strict JSON with keys: name, email, phone, company, designation, skills."
        "Use E.164 for phone if possible. skills must be an array of strings."
    )
    user = f"Resume text:\n{snippet}"

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    raw = resp.choices[0].message.content or "{}"
    fields = json.loads(raw)

    # Confidence scaffolding — adjust if you add model logits or external checks
    conf = {
        "name": 0.9 if fields.get("name") else 0.0,
        "email": 0.95 if fields.get("email") else 0.0,
        "phone": 0.9 if fields.get("phone") else 0.0,
        "company": 0.75 if fields.get("company") else 0.0,
        "designation": 0.75 if fields.get("designation") else 0.0,
    }
    if isinstance(fields.get("skills"), list):
        conf["skills"] = {s: 0.9 for s in fields["skills"]}

    return fields, conf, model

