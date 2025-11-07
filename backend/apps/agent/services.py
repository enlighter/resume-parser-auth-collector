from __future__ import annotations

from typing import Dict, Optional

from django.conf import settings
from django.utils import timezone
from itsdangerous import URLSafeSerializer

from apps.candidates.models import Candidate
from .models import AgentMessage
from .templates import build_request_documents_email, build_request_documents_sms
from .stubs import send_email, send_sms


def pick_channel(candidate: Candidate, preferred: Optional[str] = None) -> Optional[str]:
    """
    Simple policy: prefer preferred; else EMAIL if we have email; else SMS if we have phone; else None.
    """
    if preferred in (AgentMessage.Channel.EMAIL, AgentMessage.Channel.SMS):
        if preferred == AgentMessage.Channel.EMAIL and candidate.primary_email:
            return AgentMessage.Channel.EMAIL
        if preferred == AgentMessage.Channel.SMS and candidate.primary_phone:
            return AgentMessage.Channel.SMS

    if candidate.primary_email:
        return AgentMessage.Channel.EMAIL
    if candidate.primary_phone:
        return AgentMessage.Channel.SMS
    return None


def make_magic_link(candidate: Candidate) -> str:
    """
    Generates a simple signed link token for uploads (portal is optional in this MVP).
    """
    base = "http://localhost:8000"
    s = URLSafeSerializer(settings.SECRET_KEY, salt="doc-request")
    token = s.dumps({"cid": candidate.id, "ts": timezone.now().isoformat()})
    return f"{base}/portal/upload?t={token}"


def send_request_documents(
    candidate: Candidate,
    *,
    preferred_channel: Optional[str] = None,
    link_url: Optional[str] = None,
    extra_meta: Optional[Dict] = None,
) -> Dict:
    """
    Generate a personalized request, pick a channel, send via stubs, and log an AgentMessage.
    Returns a dict: {channel, status, subject?, body, link}
    """
    channel = pick_channel(candidate, preferred=preferred_channel)
    if not channel:
        # Nothing to send to
        msg = AgentMessage.objects.create(
            candidate=candidate,
            channel=AgentMessage.Channel.EMAIL,  # arbitrary default
            direction=AgentMessage.Direction.OUT,
            subject="Unable to send document request",
            body="No contact method (email/phone) available.",
            status=AgentMessage.Status.FAILED,
            meta_json={"reason": "no_contact", **(extra_meta or {})},
        )
        return {"channel": None, "status": "FAILED", "message": msg.body}

    link_url = link_url or make_magic_link(candidate)

    if channel == AgentMessage.Channel.EMAIL:
        subject, body = build_request_documents_email(candidate, link_url)
        try:
            send_email(candidate.primary_email, subject, body)
            AgentMessage.objects.create(
                candidate=candidate,
                channel=AgentMessage.Channel.EMAIL,
                direction=AgentMessage.Direction.OUT,
                subject=subject,
                body=body,
                status=AgentMessage.Status.SENT,
                meta_json={"link": link_url, **(extra_meta or {})},
            )
            return {"channel": "EMAIL", "status": "SENT", "subject": subject, "body": body, "link": link_url}
        except Exception as e:  # noqa: BLE001
            AgentMessage.objects.create(
                candidate=candidate,
                channel=AgentMessage.Channel.EMAIL,
                direction=AgentMessage.Direction.OUT,
                subject=subject,
                body=body,
                status=AgentMessage.Status.FAILED,
                error=str(e),
                meta_json={"link": link_url, **(extra_meta or {})},
            )
            return {"channel": "EMAIL", "status": "FAILED", "error": str(e), "link": link_url}

    # SMS path
    sms_body = build_request_documents_sms(candidate, link_url)
    try:
        send_sms(candidate.primary_phone, sms_body)
        AgentMessage.objects.create(
            candidate=candidate,
            channel=AgentMessage.Channel.SMS,
            direction=AgentMessage.Direction.OUT,
            subject="",
            body=sms_body,
            status=AgentMessage.Status.SENT,
            meta_json={"link": link_url, **(extra_meta or {})},
        )
        return {"channel": "SMS", "status": "SENT", "body": sms_body, "link": link_url}
    except Exception as e:  # noqa: BLE001
        AgentMessage.objects.create(
            candidate=candidate,
            channel=AgentMessage.Channel.SMS,
            direction=AgentMessage.Direction.OUT,
            subject="",
            body=sms_body,
            status=AgentMessage.Status.FAILED,
            error=str(e),
            meta_json={"link": link_url, **(extra_meta or {})},
        )
        return {"channel": "SMS", "status": "FAILED", "error": str(e), "link": link_url}
