from __future__ import annotations

from copy import deepcopy
import logging
from typing import Any, Dict, Optional

import yaml

from utils.fs_manager import FileSystemManager
from .config_schema import AppConfig, build_app_config
from .errors import ConfigError


DEFAULT_SETTINGS: dict[str, Any] = {
    "version": 2,
    "site": {
        "name": "Website Generator",
        "description": "",
        "base_url": "",
        "author": "",
        "navigation": [],
    },
    "content": {
        "source_directory": "./source",
        "data_dir": "./source/data",
        "models": {},
        "collections": {},
    },
    "theme": {
        "name": "minimal-blog",
        "settings": "./theme.settings.yaml",
        "site_theme_dir": "./site-theme",
        "extra_css_urls": [],
        "extra_js_urls": [],
        "customizer": {},
    },
    "build": {
        "output_directory": "./output",
        "asset_dirs": ["./source/assets"],
        "template_engine": "django",
        "template_dirs": [],
        "log_level": 20,
        "strict": True,
        "incremental": False,
    },
    "extensions": {
        "enabled": [],
        "local_paths": ["./extensions"],
    },
    "frontend": {
        "targets": [],
        "islands": [],
    },
    "runtime": {
        "targets": [],
        "catalog_snapshot": {
            "enabled": False,
            "target": "",
            "url_path": "/catalog/snapshot",
            "output_dir": "./output/data/runtime",
        },
    },
    "integrations": {},
    "plugins": [],
    "experimental": {
        "react": {
            "enabled": False,
            "collection": "",
            "app_dir": "./react-app",
            "export_subdir": "",
            "base_path": "",
            "asset_prefix": "",
        },
        "export_data": {
            "enabled": False,
            "output_dir": "./output/data",
            "include_collections": [],
        },
        "tailwind": {
            "enabled": False,
            "input": "./styles/tailwind.input.css",
            "output": "./styles/tailwind.css",
            "config": "./tailwind.config.js",
            "minify": False,
        },
    },
}


class Config:
    """Loads, validates, and exposes project settings.

    Configuration uses a single nested schema (``site``, ``content``, ``theme``,
    ``build``, ``frontend``, ``runtime``, ``integrations``, ``experimental``).
    There is exactly one canonical representation: the normalized ``settings``
    mapping. :attr:`schema` is a typed, read-only projection of that mapping for
    ergonomic, autocompletion-friendly access from the SSG core; it never holds
    independent state.

    Loading fails loudly: a missing or malformed config raises
    :class:`core.errors.ConfigError` rather than silently falling back to
    defaults.
    """

    def __init__(self, fs_manager: Optional[FileSystemManager] = None) -> None:
        self.logger = logging.getLogger(__name__)
        self.fs_manager = fs_manager or FileSystemManager()
        self.settings: Dict[str, Any] = deepcopy(DEFAULT_SETTINGS)
        self.warnings: list[str] = []
        self.schema: AppConfig = build_app_config(self.settings)

    # -- loading -----------------------------------------------------------

    def load(self, filepath: str) -> None:
        """Load configuration from a YAML file, failing loudly on errors."""
        self.logger.debug("Loading config from '%s'", filepath)
        self.warnings = []

        try:
            file_content = self.fs_manager.read_file(filepath)
        except FileNotFoundError as exc:
            raise ConfigError(f"Config file not found: {filepath}") from exc
        except OSError as exc:
            raise ConfigError(f"Could not read config file '{filepath}': {exc}") from exc

        try:
            loaded_settings = yaml.safe_load(file_content) or {}
        except yaml.YAMLError as exc:
            raise ConfigError(f"Invalid YAML in config file '{filepath}': {exc}") from exc

        if not isinstance(loaded_settings, dict):
            raise ConfigError("Config root element must be a mapping (dictionary).")

        normalized_settings = self._normalize_settings(loaded_settings)
        self.settings = self._deep_merge_dicts(
            deepcopy(DEFAULT_SETTINGS), normalized_settings
        )
        self._rebuild_schema()

        self.logger.info(
            "Config loaded from '%s' with keys: %s",
            filepath,
            list(self.settings.keys()),
        )
        for warning in self.warnings:
            self.logger.warning(warning)

    # -- accessors ---------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a configuration value via a dotted path such as ``theme.name``."""
        if "." not in key:
            return self.settings.get(key, default)

        cursor: Any = self.settings
        for part in key.split("."):
            if not isinstance(cursor, dict) or part not in cursor:
                return default
            cursor = cursor[part]
        return cursor

    def set(self, key: str, value: Any) -> None:
        """Set or update a top-level configuration setting."""
        self.settings[key] = value
        self._rebuild_schema()
        self.logger.debug("Config setting updated: %s = %s", key, value)

    def get_keys(self) -> list[str]:
        """Return all top-level configuration keys."""
        return list(self.settings.keys())

    def _rebuild_schema(self) -> None:
        self.schema = build_app_config(self.settings)

    # -- validation --------------------------------------------------------

    def validate(self) -> None:
        """Validate the loaded configuration and collect deprecation warnings."""
        version = self.get("version")
        if version not in {1, 2}:
            raise ConfigError(
                f"Unsupported config version: {version!r}. Supported versions are 1 and 2. "
                "Use 'version: 2' for new projects."
            )

        if version == 1:
            self.warnings.append(
                "Config version 1 is deprecated. Please migrate to version 2 for new projects."
            )

        template_engine = self.get("build.template_engine", "django")
        if template_engine != "django":
            raise ConfigError(
                "Unsupported template engine: '%s'. The only supported engine is 'django'."
                % template_engine
            )

        runtime_targets = self.get("runtime.targets", [])
        allowed_runtime_types = {"django_service", "fastapi_service", "mock_runtime"}
        if isinstance(runtime_targets, list):
            for raw_target in runtime_targets:
                if not isinstance(raw_target, dict):
                    continue
                target_type = str(raw_target.get("type", "")).strip()
                if target_type == "fastapi_service":
                    self.warnings.append(
                        "runtime.targets[].type 'fastapi_service' is deprecated; "
                        "use 'django_service' instead."
                    )
                elif target_type and target_type not in allowed_runtime_types:
                    self.warnings.append(
                        "runtime.targets[].type '%s' is not recognized; "
                        "supported values are 'django_service', 'fastapi_service', and 'mock_runtime'."
                        % target_type
                    )
        elif runtime_targets is not None:
            self.warnings.append(
                "runtime.targets should be a list of runtime target definitions."
            )

        catalog_snapshot = self.get("runtime.catalog_snapshot")
        if catalog_snapshot is not None and not isinstance(catalog_snapshot, dict):
            self.warnings.append(
                "runtime.catalog_snapshot should be a mapping of snapshot settings."
            )

        collections = self.get("content.collections", {})
        uses_runtime_catalog = False
        if isinstance(collections, dict):
            for raw_cfg in collections.values():
                if isinstance(raw_cfg, dict) and str(raw_cfg.get("type", "")).strip() == "runtime_catalog":
                    uses_runtime_catalog = True
                    break

        snapshot_enabled = (
            isinstance(catalog_snapshot, dict)
            and catalog_snapshot.get("enabled") is True
        )

        if uses_runtime_catalog and not snapshot_enabled:
            self.warnings.append(
                "A collection uses type 'runtime_catalog' but runtime.catalog_snapshot.enabled is not true."
            )

        if snapshot_enabled:
            named_targets: list[str] = []
            if isinstance(runtime_targets, list):
                for raw_target in runtime_targets:
                    if isinstance(raw_target, dict):
                        named_targets.append(str(raw_target.get("name", "")).strip())

            if not named_targets:
                self.warnings.append(
                    "runtime.catalog_snapshot.enabled is true but no runtime.targets are configured."
                )

            target_name = str(catalog_snapshot.get("target", "")).strip()
            if target_name and target_name not in named_targets:
                self.warnings.append(
                    "runtime.catalog_snapshot.target '%s' was not found in runtime.targets[].name."
                    % target_name
                )

        self._validate_integration_provider_maps()

    def _validate_integration_provider_maps(self) -> None:
        integrations_cfg = self.get("integrations", {})
        if not isinstance(integrations_cfg, dict):
            self.warnings.append("integrations should be a mapping.")
            return

        provider_domains = ["payments", "notifications", "shipping", "accounting", "tax"]
        for domain in provider_domains:
            domain_cfg = integrations_cfg.get(domain)
            if domain_cfg is None:
                continue
            if not isinstance(domain_cfg, dict):
                self.warnings.append(f"integrations.{domain} should be a mapping.")
                continue

            default_provider = domain_cfg.get("default", "")
            providers = domain_cfg.get("providers", {})
            if default_provider is not None and not isinstance(default_provider, str):
                self.warnings.append(f"integrations.{domain}.default should be a string.")
            if providers is not None and not isinstance(providers, dict):
                self.warnings.append(f"integrations.{domain}.providers should be a mapping.")
                continue
            if isinstance(providers, dict) and providers and not str(default_provider).strip():
                self.warnings.append(
                    f"integrations.{domain}.providers is configured but integrations.{domain}.default is empty."
                )

            if isinstance(providers, dict):
                for provider_name, provider_cfg in providers.items():
                    if not isinstance(provider_cfg, dict):
                        self.warnings.append(
                            f"integrations.{domain}.providers.{provider_name} should be a mapping."
                        )
                        continue
                    adapter_name = provider_cfg.get("adapter")
                    if adapter_name is None or not str(adapter_name).strip():
                        self.warnings.append(
                            f"integrations.{domain}.providers.{provider_name}.adapter is required."
                        )

    # -- normalization -----------------------------------------------------

    def _normalize_settings(self, loaded_settings: dict[str, Any]) -> dict[str, Any]:
        """Normalize a nested config mapping into the canonical v2 shape.

        Unknown top-level keys are preserved. Collections are normalized so the
        build pipeline can rely on ``route.prefix``, ``type``, ``model``,
        ``layout``, ``defaults`` and ``index`` always being present.
        """
        normalized = deepcopy(loaded_settings)
        self._finalize_shape(normalized)
        return normalized

    def _finalize_shape(self, normalized: dict[str, Any]) -> None:
        normalized.setdefault("version", 2)
        for section, default in (
            ("site", DEFAULT_SETTINGS["site"]),
            ("content", DEFAULT_SETTINGS["content"]),
            ("theme", DEFAULT_SETTINGS["theme"]),
            ("build", DEFAULT_SETTINGS["build"]),
            ("extensions", DEFAULT_SETTINGS["extensions"]),
            ("frontend", DEFAULT_SETTINGS["frontend"]),
            ("runtime", DEFAULT_SETTINGS["runtime"]),
            ("experimental", DEFAULT_SETTINGS["experimental"]),
        ):
            if not isinstance(normalized.get(section), dict):
                normalized[section] = deepcopy(default)
        normalized.setdefault("integrations", {})
        normalized.setdefault("plugins", [])

        content = normalized["content"]
        content.setdefault("models", {})

        self._normalize_collections(content)
        self._synthesize_react_frontend_target(normalized)

    def _normalize_collections(self, content: dict[str, Any]) -> None:
        collections = content.get("collections", {})
        if not isinstance(collections, dict):
            collections = {}
            content["collections"] = collections

        for name, raw_cfg in list(collections.items()):
            if not isinstance(raw_cfg, dict):
                collections[name] = {"path": str(raw_cfg)}
                raw_cfg = collections[name]

            route = raw_cfg.get("route", {})
            if not isinstance(route, dict):
                route = {}

            legacy_prefix = raw_cfg.get("url_prefix")
            if legacy_prefix and "prefix" not in route:
                route["prefix"] = legacy_prefix
                self.warnings.append(
                    f"Collection '{name}' uses deprecated 'url_prefix'; normalized to 'route.prefix'."
                )

            if "prefix" not in route:
                route["prefix"] = "" if name == "pages" else raw_cfg.get("type", name)

            raw_cfg["route"] = route
            raw_cfg.setdefault("type", name)
            raw_cfg.setdefault("model", self._infer_collection_model(name, raw_cfg))
            raw_cfg.setdefault("layout", raw_cfg.get("template", "document"))

            defaults = raw_cfg.get("defaults", {})
            if not isinstance(defaults, dict):
                defaults = {}
            defaults.setdefault("layout", raw_cfg.get("layout", "document"))
            raw_cfg["defaults"] = defaults

            index_cfg = raw_cfg.get("index", {})
            if not isinstance(index_cfg, dict):
                index_cfg = {}
            if index_cfg.get("enabled", False):
                index_cfg.setdefault("layout", "collection")
                index_cfg.setdefault("title", name.replace("-", " ").title())
            raw_cfg["index"] = index_cfg

    def _synthesize_react_frontend_target(self, normalized: dict[str, Any]) -> None:
        experimental = normalized.get("experimental", {})
        frontend = normalized.get("frontend", {})
        react_cfg = experimental.get("react", {}) if isinstance(experimental, dict) else {}
        frontend_targets = frontend.get("targets", []) if isinstance(frontend, dict) else []
        if not isinstance(frontend_targets, list):
            frontend_targets = []

        if isinstance(react_cfg, dict) and react_cfg.get("enabled", False):
            frontend_targets.append(
                {
                    "type": "spa_subtree",
                    "name": react_cfg.get("collection") or "react-section",
                    "framework": "next_static_export",
                    "collection": react_cfg.get("collection", ""),
                    "app_dir": react_cfg.get("app_dir", "./react-app"),
                    "export_subdir": react_cfg.get("export_subdir") or react_cfg.get("collection", ""),
                    "base_path": react_cfg.get("base_path", ""),
                    "asset_prefix": react_cfg.get("asset_prefix", ""),
                }
            )
            self.warnings.append(
                "experimental.react is deprecated; a frontend.targets entry was synthesized."
            )
        if isinstance(frontend, dict):
            frontend["targets"] = frontend_targets

    def _infer_collection_model(self, name: str, raw_cfg: dict[str, Any]) -> str:
        collection_type = str(raw_cfg.get("type", name))
        model_map = {
            "blog": "post",
            "post": "post",
            "page": "page",
            "pages": "page",
            "doc": "doc",
            "docs": "doc",
            "shop": "product",
            "product": "product",
            "category": "category",
            "landing": "landing",
            "event": "event",
        }
        return model_map.get(collection_type, collection_type)

    def _deep_merge_dicts(
        self, base: Dict[str, Any], updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key] = self._deep_merge_dicts(base[key], value)
            else:
                base[key] = value
        return base
