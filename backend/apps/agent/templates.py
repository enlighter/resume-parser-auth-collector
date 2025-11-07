from __future__ import annotations

from typing import Tuple

from apps.candidates.models import Candidate


def build_request_documents_email(candidate: Candidate, link_url: str) -> Tuple[str, str]:
    name = candidate.name or "Candidate"
    subject = "Request for PAN/Aadhaar documents"
    body = (
        f"Hi {name},\n\n"
        "To complete verification, please upload your PAN and Aadhaar.\n"
        f"Secure upload link: {link_url}\n\n"
        "If you have questions, just reply to this email.\n"
        "Thanks!"
    )
    return subject, body


def build_request_documents_sms(candidate: Candidate, link_url: str) -> str:
    name = candidate.name.split()[0] if candidate.name else "there"
    return (
        f"Hi {name}, please upload PAN & Aadhaar to complete verification: {link_url}"
    )
