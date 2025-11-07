from django.apps import AppConfig


class CandidatesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.candidates"

    def ready(self) -> None:
        super().ready()
        # Import signal handlers when the app is ready.
        from . import signals  # noqa: F401
