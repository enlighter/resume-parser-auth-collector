from __future__ import annotations

from typing import Any, Dict, Optional

from django.conf import settings
from django.core.mail import send_mail
from rest_framework import serializers

from apps.candidates.models import Candidate
from .models import Document, DocumentRequest, DocumentSubmission
from .validators import (
    is_valid_pan,
    is_valid_aadhaar,
    sniff_mime,
    is_allowed_mime,
)


class SubmitDocumentsSerializer(serializers.Serializer):
    pan_file = serializers.FileField(required=False, allow_null=True)
    aadhaar_file = serializers.FileField(required=False, allow_null=True)
    pan_number = serializers.CharField(required=False, allow_blank=True)
    aadhaar_number = serializers.CharField(required=False, allow_blank=True)
    source = serializers.ChoiceField(choices=DocumentSubmission.Source.choices, default=DocumentSubmission.Source.STAFF)

    def validate(self, attrs):
        if not attrs.get("pan_file") and not attrs.get("aadhaar_file"):
            raise serializers.ValidationError("Provide at least one file: pan_file or aadhaar_file.")
        return attrs

    def _save_one(
        self,
        *,
        candidate: Candidate,
        kind: str,
        fobj,
        number: Optional[str],
    ) -> Document:
        doc = Document(candidate=candidate, kind=kind)

        # Set meta from file
        filename = getattr(fobj, "name", f"{kind.lower()}.bin")
        first_bytes = fobj.read(4096)
        fobj.seek(0)
        mime = sniff_mime(first_bytes, filename)
        if not mime:
            mime = getattr(fobj, "content_type", "") or ""
        if not is_allowed_mime(mime):
            raise serializers.ValidationError(f"{kind} must be a JPEG/PNG/PDF file.")
        size = getattr(fobj, "size", None)
        if size is None:
            try:
                pos = fobj.tell()
                fobj.seek(0, 2)
                size = fobj.tell()
                fobj.seek(pos)
            except Exception:
                size = 0

        max_mb = int(getattr(settings, "MAX_UPLOAD_MB", 10))
        if size and size > max_mb * 1024 * 1024:
            raise serializers.ValidationError(f"{kind} too large (>{max_mb} MB).")

        doc.mime_type = mime
        doc.size_bytes = size or 0
        doc.file.save(filename, fobj, save=False)
        doc.save()  # need pk for path; the save above may also persist

        # compute hash post-save to read the stored file
        doc.compute_sha256()

        verified = {"mime_ok": True}

        if kind == Document.Kind.PAN and number:
            valid = is_valid_pan(number.strip().upper())
            verified["pattern_valid"] = bool(valid)
            doc.masked_number = number[-4:] if number else ""
        elif kind == Document.Kind.AADHAAR and number:
            v = number.strip().replace(" ", "")
            valid = is_valid_aadhaar(v)
            verified["pattern_valid"] = bool(valid)
            doc.masked_number = v[-4:] if v else ""

        doc.verified_flags_json = verified
        doc.save(update_fields=["sha256", "verified_flags_json", "masked_number"])

        return doc

    def create(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        candidate: Candidate = self.context["candidate"]
        request_obj: Optional[DocumentRequest] = self.context.get("document_request")

        pan_doc = None
        aadhaar_doc = None

        if validated_data.get("pan_file"):
            pan_doc = self._save_one(
                candidate=candidate,
                kind=Document.Kind.PAN,
                fobj=validated_data["pan_file"],
                number=(validated_data.get("pan_number") or "").upper(),
            )

        if validated_data.get("aadhaar_file"):
            aadhaar_doc = self._save_one(
                candidate=candidate,
                kind=Document.Kind.AADHAAR,
                fobj=validated_data["aadhaar_file"],
                number=validated_data.get("aadhaar_number") or "",
            )

        sub = DocumentSubmission.objects.create(
            request=request_obj,
            candidate=candidate,
            pan_document=pan_doc,
            aadhaar_document=aadhaar_doc,
            source=validated_data.get("source") or DocumentSubmission.Source.STAFF,
        )

        # if both uploaded, you might choose to mark latest request as completed
        if request_obj and (pan_doc or aadhaar_doc):
            request_obj.status = DocumentRequest.Status.COMPLETED
            request_obj.save(update_fields=["status"])

        return {
            "submission_id": sub.id,
            "pan_document_id": pan_doc.id if pan_doc else None,
            "aadhaar_document_id": aadhaar_doc.id if aadhaar_doc else None,
        }


class SubmitDocumentsResponseSerializer(serializers.Serializer):
    submission_id = serializers.IntegerField()
    pan_document_id = serializers.IntegerField(allow_null=True)
    aadhaar_document_id = serializers.IntegerField(allow_null=True)


class RequestDocumentsSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(choices=DocumentRequest.Channel.choices, default=DocumentRequest.Channel.EMAIL)

    def create(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        from itsdangerous import URLSafeSerializer

        candidate: Candidate = self.context["candidate"]
        channel = validated_data["channel"]

        # Simple token & link (you can later add an actual portal endpoint)
        s = URLSafeSerializer(settings.SECRET_KEY, salt="doc-request")
        token = s.dumps({"cid": candidate.id})
        link = f"http://localhost:8000/portal/upload?t={token}"

        msg = (
            f"Hi {candidate.name or 'Candidate'},\n\n"
            "Please share your PAN and Aadhaar to complete verification.\n"
            f"Upload securely here: {link}\n\n"
            "Thanks!"
        )
        req = DocumentRequest.objects.create(
            candidate=candidate,
            channel=channel,
            status=DocumentRequest.Status.SENT,
            message_preview=msg,
            magic_token=token,
            link_url=link,
        )

        # Send via console email or log-SMS
        if channel == DocumentRequest.Channel.EMAIL and candidate.primary_email:
            send_mail(
                subject="Request for PAN/Aadhaar",
                message=msg,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "Dev <dev@localhost>"),
                recipient_list=[candidate.primary_email],
                fail_silently=True,
            )
        elif channel == DocumentRequest.Channel.SMS and candidate.primary_phone:
            # minimal SMS stub
            print(f"[SMS → {candidate.primary_phone}] {msg}")  # noqa: T201

        return {
            "request_id": req.id,
            "channel": req.channel,
            "status": req.status,
            "link": link,
            "message_preview": msg,
        }


class RequestDocumentsResponseSerializer(serializers.Serializer):
    request_id = serializers.IntegerField()
    channel = serializers.CharField()
    status = serializers.CharField()
    link = serializers.CharField()
    message_preview = serializers.CharField()
