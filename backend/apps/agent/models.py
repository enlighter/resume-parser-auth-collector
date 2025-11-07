from __future__ import annotations

from django.db import models
from django.utils import timezone

from apps.candidates.models import Candidate


class AgentMessage(models.Model):
    class Channel(models.TextChoices):
        EMAIL = "EMAIL", "Email"
        SMS = "SMS", "SMS"

    class Direction(models.TextChoices):
        OUT = "OUT", "Outgoing"
        IN = "IN", "Incoming"

    class Status(models.TextChoices):
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="agent_messages")
    channel = models.CharField(max_length=16, choices=Channel.choices)
    direction = models.CharField(max_length=8, choices=Direction.choices, default=Direction.OUT)

    subject = models.CharField(max_length=255, blank=True, default="")
    body = models.TextField(blank=True, default="")

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SENT)
    error = models.TextField(blank=True, default="")

    meta_json = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        who = self.candidate_id or "?"
        return f"{self.channel}/{self.direction} → {who} [{self.status}]"
