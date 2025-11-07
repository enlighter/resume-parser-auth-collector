from __future__ import annotations

from django.conf import settings
from django.core.mail import send_mail


def send_email(to_email: str, subject: str, body: str) -> None:
    """
    Uses Django's configured backend (console by default in settings.py).
    """
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "Dev <dev@localhost>")
    if not to_email:
        raise ValueError("Missing recipient email")
    send_mail(subject=subject, message=body, from_email=from_email, recipient_list=[to_email], fail_silently=False)


def send_sms(to_phone: str, body: str) -> None:
    """
    Console-only SMS stub. Replace with provider integration later.
    """
    if not to_phone:
        raise ValueError("Missing recipient phone")
    print(f"[SMS → {to_phone}] {body}")  # noqa: T201
