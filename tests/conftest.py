"""Shared test configuration and fixtures.

This replaces the per-module ``sys.path`` hacks, module-level ``migrate`` calls,
and pid-keyed temp databases that previously made tests order-dependent and
leaky. Django tests now get a clean, isolated database per test via
``pytest-django`` (``@pytest.mark.django_db``), and the runtime integration
context cache is reset around every test.
"""

from __future__ import annotations

import pytest

# Environment defaults are set in the repository-root conftest.py, which loads
# before Django settings are first accessed by pytest-django.


@pytest.fixture(autouse=True)
def _reset_runtime_integration_cache():
    """Ensure each test sees a freshly resolved runtime integration context."""
    try:
        from wg_runtime.runtime.integrations import (
            reset_runtime_integration_context_cache,
        )
    except Exception:
        yield
        return

    reset_runtime_integration_context_cache()
    yield
    reset_runtime_integration_context_cache()
