"""Runtime-local adapter registry and configuration loading.

This is the seam that lets the Django runtime resolve integration adapters and
configuration WITHOUT importing the static-site generator (``core.*``). The
former implementation re-bootstrapped the whole SSG config on every cold
request; the runtime now owns a small registry populated from Django settings.

Dependency direction: ``wg_runtime`` -> ``wg_contracts`` (+ adapter packages by
dotted path). It no longer depends on ``core``.
"""

from __future__ import annotations

import importlib
import os
from copy import deepcopy
from typing import Any

import yaml
from django.conf import settings


class RuntimeAdapterRegistry:
    """Named registry of integration adapter classes and their metadata."""

    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}

    def register(self, name: str, value: Any, *, metadata: dict[str, Any] | None = None) -> None:
        self._items[str(name)] = {"value": value, "metadata": deepcopy(metadata or {})}

    def get(self, name: str, default: Any = None) -> Any:
        entry = self._items.get(str(name))
        return default if entry is None else entry["value"]

    def describe(self, name: str) -> dict[str, Any]:
        entry = self._items.get(str(name), {})
        metadata_value = entry.get("metadata", {})
        return deepcopy(metadata_value if isinstance(metadata_value, dict) else {})

    def names(self) -> list[str]:
        return list(self._items.keys())


def _resolve_dotted(path: str) -> Any:
    module_name, _, attr = path.partition(":")
    attr = attr or "get_extension"
    module = importlib.import_module(module_name)
    obj = getattr(module, attr)
    return obj() if callable(obj) else obj


def load_integrations_from_yaml_path(config_path: str) -> dict[str, Any]:
    """Load integrations from a YAML file without Django settings."""
    if not config_path or not os.path.exists(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    integrations = raw.get("integrations", {}) if isinstance(raw, dict) else {}
    return deepcopy(integrations) if isinstance(integrations, dict) else {}


def load_yaml_config(config_path: str) -> dict[str, Any]:
    """Load a full YAML site config without the SSG config loader."""
    if not config_path or not os.path.exists(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return deepcopy(raw) if isinstance(raw, dict) else {}


def build_adapter_registry_for_providers(
    providers: list[str] | None = None,
) -> RuntimeAdapterRegistry:
    """Build an adapter registry from dotted provider paths (no Django required)."""
    registry = RuntimeAdapterRegistry()
    provider_paths = providers or ["wg_commerce.extension:get_extension"]
    for provider_path in provider_paths:
        provider = _resolve_dotted(str(provider_path))
        register = getattr(provider, "register_runtime_adapters", None)
        if callable(register):
            register(registry)
    return registry


def build_adapter_registry() -> RuntimeAdapterRegistry:
    """Populate the registry from the configured adapter providers.

    Providers are dotted ``module:callable`` strings (Django setting
    ``WG_RUNTIME_ADAPTER_PROVIDERS``) returning an object exposing
    ``register_runtime_adapters(registry)``. Defaults to the commerce adapters.
    """
    providers = getattr(
        settings,
        "WG_RUNTIME_ADAPTER_PROVIDERS",
        ["wg_commerce.extension:get_extension"],
    )
    return build_adapter_registry_for_providers(list(providers))


def load_integrations_config() -> dict[str, Any]:
    """Load the integrations provider map.

    Priority: Django setting ``WG_INTEGRATIONS`` (a mapping), else the
    ``integrations`` section of the YAML config file referenced by
    ``WG_RUNTIME_CONFIG_PATH`` / ``WG_CONFIG_PATH``. Read directly with PyYAML;
    no dependency on the SSG config loader.
    """
    configured = getattr(settings, "WG_INTEGRATIONS", None)
    if isinstance(configured, dict):
        return deepcopy(configured)

    config_path = (
        os.environ.get("WG_RUNTIME_CONFIG_PATH")
        or os.environ.get("RUNTIME_CONFIG_PATH")
        or os.environ.get("WG_CONFIG_PATH")
        or getattr(settings, "WG_CONFIG_PATH", "")
    )
    return load_integrations_from_yaml_path(str(config_path))
