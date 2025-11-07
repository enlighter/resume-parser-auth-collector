from __future__ import annotations

from typing import Any, Dict, Optional

from django.utils import timezone
from rest_framework import serializers

from .models import Candidate, Resume, Extraction


class CandidateListSerializer(serializers.ModelSerializer):
    email = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()

    class Meta:
        model = Candidate
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "latest_company",
            "extraction_status",
            "created_at",
        ]

    def get_email(self, obj: Candidate) -> str:
        return obj.masked_email()

    def get_phone(self, obj: Candidate) -> str:
        return obj.masked_phone()


class CandidateDetailSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    documents = serializers.SerializerMethodField()

    class Meta:
        model = Candidate
        fields = [
            "id",
            "profile",
            "extraction_status",
            "documents",
            "created_at",
            "updated_at",
        ]

    def _latest_extraction(self, obj: Candidate) -> Optional[Extraction]:
        return obj.extractions.order_by("-created_at").first()

    def get_profile(self, obj: Candidate) -> Dict[str, Any]:
        ex = self._latest_extraction(obj)
        fields = ex.fields_json if ex else {}
        conf = ex.confidences_json if ex else {}
        # Provide confidence-wrapped structure expected by the UI.
        def pack(key: str, default: str = "") -> Dict[str, Any]:
            return {"value": fields.get(key, default), "confidence": conf.get(key, 0.0)}

        skills = fields.get("skills", [])
        skills_conf = conf.get("skills", {})
        skills_payload = [
            {"name": s, "confidence": float(skills_conf.get(s, 0.0))}
            for s in skills
        ]

        return {
            "name": pack("name", obj.name),
            "email": {"value": obj.primary_email, "confidence": conf.get("email", 0.0), "masked": obj.masked_email()},
            "phone": {"value": obj.primary_phone, "confidence": conf.get("phone", 0.0), "masked": obj.masked_phone()},
            "company": pack("company", obj.latest_company),
            "designation": pack("designation", obj.designation),
            "skills": skills_payload,
            "model_name": ex.model_name if ex else "n/a",
            "extracted_at": ex.completed_at.isoformat() if ex and ex.completed_at else None,
        }

    def get_documents(self, obj: Candidate) -> Dict[str, Any]:
        # Stub structure; real docs live in documents app.
        return {
            "PAN": {"present": False, "verified": False},
            "AADHAAR": {"present": False, "verified": False},
        }


class ResumeUploadResponseSerializer(serializers.Serializer):
    candidate_id = serializers.IntegerField()
    resume_id = serializers.IntegerField()
    status = serializers.CharField()
    message = serializers.CharField()


class ResumeUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def create(self, validated_data):
        # Not used (we handle in the view).
        return validated_data

    def validate_file(self, f):
        max_mb = int(self.context.get("MAX_UPLOAD_MB", 10))
        if f.size > max_mb * 1024 * 1024:
            raise serializers.ValidationError(f"File too large (>{max_mb} MB).")
        # Minimal content type check; deeper sniffing can be added.
        allowed = {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
        if getattr(f, "content_type", None) not in allowed:
            # Let PDFs without content_type slide in some browsers.
            name = (getattr(f, "name", "") or "").lower()
            if not (name.endswith(".pdf") or name.endswith(".docx")):
                raise serializers.ValidationError("Only PDF or DOCX resumes are supported.")
        return f
