from __future__ import annotations

from django.db import models
from django.utils import timezone


class Candidate(models.Model):
    class ExtractionStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PARSING = "PARSING", "Parsing"
        PARSED = "PARSED", "Parsed"
        FAILED = "FAILED", "Failed"

    name = models.CharField(max_length=255, blank=True, default="")
    primary_email = models.EmailField(blank=True, default="")
    primary_phone = models.CharField(max_length=32, blank=True, default="")
    latest_company = models.CharField(max_length=255, blank=True, default="")
    designation = models.CharField(max_length=255, blank=True, default="")
    extraction_status = models.CharField(
        max_length=16, choices=ExtractionStatus.choices, default=ExtractionStatus.PENDING
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def masked_email(self) -> str:
        v = (self.primary_email or "").strip()
        if not v or "@" not in v:
            return ""
        user, domain = v.split("@", 1)
        if len(user) <= 1:
            masked_user = "*"
        else:
            masked_user = user[0] + "*" * max(1, len(user) - 1)
        return f"{masked_user}@{domain}"

    def masked_phone(self) -> str:
        v = (self.primary_phone or "").strip()
        if len(v) <= 4:
            return v
        return f"{'*' * (len(v) - 4)}{v[-4:]}"

    def __str__(self) -> str:
        return self.name or f"Candidate #{self.pk}"


def resume_upload_path(instance: "Resume", filename: str) -> str:
    return f"resumes/{instance.id or 'new'}/{filename}"


class Resume(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PARSING = "PARSING", "Parsing"
        PARSED = "PARSED", "Parsed"
        FAILED = "FAILED", "Failed"

    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE, related_name="resumes"
    )
    file = models.FileField(upload_to=resume_upload_path)
    original_name = models.CharField(max_length=255, blank=True, default="")
    mime_type = models.CharField(max_length=128, blank=True, default="")
    size_bytes = models.PositiveIntegerField(default=0)

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    uploaded_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"Resume {self.original_name} for {self.candidate_id}"


class Extraction(models.Model):
    class Status(models.TextChoices):
        STARTED = "STARTED", "Started"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE, related_name="extractions"
    )
    resume = models.ForeignKey(
        Resume, on_delete=models.SET_NULL, related_name="extractions", null=True, blank=True
    )

    raw_text = models.TextField(blank=True, default="")
    fields_json = models.JSONField(default=dict)        # normalized extracted fields
    confidences_json = models.JSONField(default=dict)   # per-field confidence 0..1
    model_name = models.CharField(max_length=128, blank=True, default="heuristics")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.STARTED)

    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Extraction {self.id} for {self.candidate_id}"
