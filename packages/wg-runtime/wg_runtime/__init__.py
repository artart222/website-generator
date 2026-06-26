"""Local runtime companion utilities for dynamic integrations."""

from .celery import app as celery_app

__all__ = ["celery_app"]
