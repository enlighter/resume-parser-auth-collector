from __future__ import annotations

import threading
from django.db.models.signals import post_save
from django.db import transaction
from django.dispatch import receiver

from .models import Resume
from .parsing import parse_resume


@receiver(post_save, sender=Resume)
def parse_on_resume_create(sender, instance: Resume, created: bool, **kwargs):
    """
    When a Resume is created, kick parsing after the surrounding transaction commits.
    This duplicates queue_parse_resume in views, but also covers any programmatic creates.
    """
    if not created:
        return

    def _start():
        t = threading.Thread(target=parse_resume, args=(instance.id,), daemon=True)
        t.start()

    # Ensure DB row is visible and file committed before parsing
    transaction.on_commit(_start)
