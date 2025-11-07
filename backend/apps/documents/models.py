from __future__ import annotations

import hashlib
import os
from django.db import models
from django.utils import timezone

from apps.candidates.models import Candidate


def document_upload_path(instance: "Document", filename: str) -> str:
    base = f"docs/{instance.candidate_id}/{instance.kind.lower()}"
    # keep original filename but prevent path traversal
    name = os.path.basename(filename) or "document"
    return f"{base}/{name}"


class Document(models.Model):
    class Kind(models.TextChoices):
        PAN = "PAN", "PAN"
        AADHAAR = "AADHAAR", "Aadhaar"

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="documents")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    file = models.FileField(upload_to=document_upload_path)

    # metadata
    mime_type = models.CharField(max_length=64, blank=True, default="")
    size_bytes = models.PositiveIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True, default="")

    # optional structured verification
    masked_number = models.CharField(max_length=32, blank=True, default="")
    verified_flags_json = models.JSONField(default=dict)

    uploaded_at = models.DateTimeField(default=timezone.now)

    def compute_sha256(self) -> None:
        if not self.file:
            return
        h = hashlib.sha256()
        pos = self.file.tell()
        try:
            self.file.seek(0)
            for chunk in iter(lambda: self.file.read(8192), b""):
                h.update(chunk)
            self.sha256 = h.hexdigest()
        finally:
            self.file.seek(pos)

    def __str__(self) -> str:
        return f"{self.kind} for {self.candidate_id} ({self.id})"


class DocumentRequest(models.Model):
    class Channel(models.TextChoices):
        EMAIL = "EMAIL", "Email"
        SMS = "SMS", "SMS"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        WAITING = "WAITING", "Waiting"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="document_requests")
    channel = models.CharField(max_length=16, choices=Channel.choices, default=Channel.EMAIL)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)

    # simple content/log
    message_preview = models.TextField(blank=True, default="")
    magic_token = models.CharField(max_length=128, blank=True, default="")  # if you later create a portal
    link_url = models.URLField(blank=True, default="")

    created_at = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"DocRequest {self.channel} → {self.candidate_id} ({self.status})"


class DocumentSubmission(models.Model):
    class Source(models.TextChoices):
        PORTAL = "PORTAL", "Portal"
        STAFF = "STAFF", "Staff"

    request = models.ForeignKey(
        DocumentRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name="submissions"
    )
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="document_submissions")
    pan_document = models.ForeignKey(
        Document, on_delete=models.SET_NULL, null=True, blank=True, related_name="as_pan_submission"
    )
    aadhaar_document = models.ForeignKey(
        Document, on_delete=models.SET_NULL, null=True, blank=True, related_name="as_aadhaar_submission"
    )
    source = models.CharField(max_length=16, choices=Source.choices, default=Source.STAFF)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"Submission for {self.candidate_id} ({self.id})"
