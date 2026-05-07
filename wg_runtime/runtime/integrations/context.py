from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path
from typing import Any

from core.bootstrap import bootstrap
from core.config import Config
from core.extension_manager import ExtensionManager
from utils.fs_manager import FileSystemManager
from .contracts import (
    KIND_ACCOUNTING_EXPORTER,
    KIND_NOTIFICATION_PROVIDER,
    KIND_PAYMENT_PROVIDER,
    KIND_SHIPPING_PROVIDER,
    KIND_TAX_PRICING_PROVIDER,
)

DOMAIN_KIND_MAP = {
    "payments": KIND_PAYMENT_PROVIDER,
    "notifications": KIND_NOTIFICATION_PROVIDER,
    "shipping": KIND_SHIPPING_PROVIDER,
    "accounting": KIND_ACCOUNTING_EXPORTER,
    "tax": KIND_TAX_PRICING_PROVIDER,
}


class IntegrationResolutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderBinding:
    domain: str
    name: str
    adapter_name: str
    provider_config: dict[str, Any]


@dataclass(frozen=True)
class RuntimeIntegrationContext:
    config_path: Path | None
    config: Config
    extension_manager: ExtensionManager

    def _integration_domain_config(self, domain: str) -> tuple[str, dict[str, Any]]:
        integrations_cfg = self.config.get("integrations", {})
        if not isinstance(integrations_cfg, dict):
            return "", {}
        domain_cfg = integrations_cfg.get(domain, {})
        if not isinstance(domain_cfg, dict):
            return "", {}

        default_name = str(domain_cfg.get("default", "")).strip()
        providers = domain_cfg.get("providers", {})
        if not isinstance(providers, dict):
            return default_name, {}
        return default_name, providers

    def resolve_provider_binding(
        self,
        *,
        domain: str,
        provider_name: str = "",
    ) -> ProviderBinding | None:
        default_name, providers = self._integration_domain_config(domain)
        if not providers:
            return None

        selected = provider_name.strip() or default_name
        if selected and selected in providers:
            cfg = providers[selected]
            if isinstance(cfg, dict):
                return ProviderBinding(
                    domain=domain,
                    name=selected,
                    adapter_name=str(cfg.get("adapter", "")).strip(),
                    provider_config=dict(cfg),
                )

        if selected and selected not in providers:
            raise IntegrationResolutionError(
                f"Provider '{selected}' was not found in integrations.{domain}.providers."
            )

        for fallback_name, fallback_cfg in providers.items():
            if isinstance(fallback_cfg, dict):
                return ProviderBinding(
                    domain=domain,
                    name=str(fallback_name),
                    adapter_name=str(fallback_cfg.get("adapter", "")).strip(),
                    provider_config=dict(fallback_cfg),
                )
        return None

    def resolve_adapter(
        self,
        *,
        domain: str,
        provider_name: str = "",
    ) -> tuple[Any, ProviderBinding] | tuple[None, None]:
        binding = self.resolve_provider_binding(domain=domain, provider_name=provider_name)
        if binding is None:
            return None, None

        if not binding.adapter_name:
            raise IntegrationResolutionError(
                f"Provider '{binding.name}' in integrations.{domain}.providers is missing 'adapter'."
            )

        adapter_cls = self.extension_manager.runtime_adapter_registry.get(binding.adapter_name)
        if adapter_cls is None:
            raise IntegrationResolutionError(
                f"Adapter '{binding.adapter_name}' for integrations.{domain}.{binding.name} is not registered."
            )

        metadata = self.extension_manager.runtime_adapter_registry.describe(binding.adapter_name)
        expected_kind = DOMAIN_KIND_MAP[domain]
        actual_kind = str(metadata.get("kind", "")).strip()
        if not actual_kind:
            raise IntegrationResolutionError(
                f"Adapter '{binding.adapter_name}' is missing metadata.kind; expected '{expected_kind}'."
            )
        if actual_kind != expected_kind:
            raise IntegrationResolutionError(
                f"Adapter '{binding.adapter_name}' has kind '{actual_kind}', expected '{expected_kind}'."
            )

        return adapter_cls(), binding


def _default_config_path() -> Path:
    env_value = (
        os.environ.get("WG_RUNTIME_CONFIG_PATH")
        or os.environ.get("RUNTIME_CONFIG_PATH")
        or os.environ.get("WG_CONFIG_PATH")
    )
    if env_value:
        return Path(env_value).expanduser().resolve()
    return (Path(__file__).resolve().parents[3] / "config.yaml").resolve()


@lru_cache(maxsize=1)
def get_runtime_integration_context() -> RuntimeIntegrationContext:
    config_path = _default_config_path()
    if config_path.exists():
        config = bootstrap(config_path)
        loaded_path: Path | None = config_path
    else:
        config = Config()
        loaded_path = None

    fs_manager = FileSystemManager()
    extension_manager = ExtensionManager(config, fs_manager)
    extension_manager.detect_and_load_extensions()
    return RuntimeIntegrationContext(
        config_path=loaded_path,
        config=config,
        extension_manager=extension_manager,
    )


def reset_runtime_integration_context_cache() -> None:
    get_runtime_integration_context.cache_clear()
