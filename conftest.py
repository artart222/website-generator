"""Root conftest: prepare the environment before anything imports Django.

This is the earliest-loaded conftest, so it is the right place to choose the
test-time environment. Secure-by-default settings require DEBUG (or an explicit
secret); tests run in DEBUG with eager Celery so no broker/secret is needed.
"""

from __future__ import annotations

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wg_runtime.settings")
os.environ.setdefault("DJANGO_DEBUG", "True")
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "True")
