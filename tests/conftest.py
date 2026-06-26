"""Shared test configuration and fixtures.

This replaces the per-module ``sys.path`` hacks, module-level ``migrate`` calls,
and pid-keyed temp databases that previously made tests order-dependent and
leaky. Django tests now get a clean, isolated database per test via
``pytest-django`` (``@pytest.mark.django_db``), and the runtime integration
context cache is reset around every test.
"""

from __future__ import annotations

import json

import pytest
from django.contrib.auth.models import User
from django.test import Client

# Environment defaults are set in the repository-root conftest.py, which loads
# before Django settings are first accessed by pytest-django.


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        username="staff",
        password="staff-pass",
        is_staff=True,
    )


@pytest.fixture
def jwt_client(staff_user):
    """Django test client with a valid JWT Authorization header for staff_user."""
    client = Client()
    response = client.post(
        "/token/obtain/",
        data=json.dumps({"username": "staff", "password": "staff-pass"}),
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    access = response.json()["access"]
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {access}"
    return client


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
