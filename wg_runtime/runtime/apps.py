from django.apps import AppConfig


class RuntimeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "wg_runtime.runtime"
    verbose_name = "WG Runtime"

    def ready(self):
        # Register model signals.
        from . import signals  # noqa: F401
