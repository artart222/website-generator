from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import logging
from typing import Any, Dict, Optional

import yaml

from utils.fs_manager import FileSystemManager


DEFAULT_SETTINGS: dict[str, Any] = {
    "version": 1,
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
    """
    Loads, stores, and provides access to project settings.

    The public v1 config uses nested sections (`site`, `content`, `theme`,
    `build`, `plugins`, `experimental`). Legacy flat keys are still normalized
    into the v1 shape so the existing repository can migrate gradually.
    """

    def __init__(
        self,
        fs_manager: Optional[FileSystemManager] = None,
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.fs_manager = fs_manager or FileSystemManager()
        self.settings: Dict[str, Any] = deepcopy(DEFAULT_SETTINGS)
        self.warnings: list[str] = []
        self._apply_compat_aliases()
        self._sync_attributes_from_settings()

    def _sync_attributes_from_settings(self) -> None:
        """Expose all current top-level settings as attributes."""
        for key, value in self.settings.items():
            setattr(self, key, value)

    def validate(self) -> None:
        """Validate the loaded configuration and collect deprecation warnings."""
        version = self.get("version")
        if version not in {1, 2}:
            raise ValueError(
                f"Unsupported config version: {version!r}. Supported versions are 1 and 2. "
                "Use 'version: 2' for new projects."
            )

        if version == 1:
            self.warnings.append(
                "Config version 1 is deprecated. Please migrate to version 2 for new projects."
            )

        template_engine = self.get(
            "build.template_engine",
            self.get("template_engine", DEFAULT_SETTINGS["build"]["template_engine"]),
        )
        if template_engine != "django":
            raise ValueError(
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

    def load(self, filepath: Path = Path("./config.yaml")) -> None:
        """
        Loads configuration from YAML and normalizes it into the v1 schema.
        """
        self.logger.debug("Loading config from '%s'", filepath)
        self.warnings = []
        try:
            file_content = self.fs_manager.read_file(filepath)
            loaded_settings: Optional[dict[str, Any]] = (
                yaml.safe_load(file_content) or {}
            )

            if not isinstance(loaded_settings, dict):
                raise yaml.YAMLError("Config root element must be a dictionary")

            self.settings = deepcopy(DEFAULT_SETTINGS)
            normalized_settings = self._normalize_settings(loaded_settings)
            self.settings = self._deep_merge_dicts(
                deepcopy(self.settings), normalized_settings
            )
            self._apply_compat_aliases()
            self._sync_attributes_from_settings()

            self.logger.info(
                "Config loaded from '%s' with keys: %s",
                filepath,
                list(self.settings.keys()),
            )
            for warning in self.warnings:
                self.logger.warning(warning)

        except FileNotFoundError:
            self.logger.error("Config file not found: %s", filepath)
            self.logger.warning("Using default settings")
            self._apply_compat_aliases()
            self._sync_attributes_from_settings()
        except yaml.YAMLError:
            self.logger.error("YAML parsing error in config file '%s'", filepath)
            self.logger.warning("Using default settings")
            self._apply_compat_aliases()
            self._sync_attributes_from_settings()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value.

        Supports dotted-path lookups such as `theme.name`.
        """
        if "." not in key:
            return self.settings.get(key, default)

        cursor: Any = self.settings
        for part in key.split("."):
            if not isinstance(cursor, dict) or part not in cursor:
                return default
            cursor = cursor[part]
        return cursor

    def set(self, key: str, value: Any) -> None:
        """
        Sets or updates a top-level configuration setting.
        """
        self.settings[key] = value
        if hasattr(self, key):
            setattr(self, key, value)
        self.logger.debug("Config setting updated: %s = %s", key, value)

    def get_keys(self) -> list[str]:
        """Returns all top-level configuration keys."""
        return list(self.settings.keys())

    def _normalize_settings(self, loaded_settings: dict[str, Any]) -> dict[str, Any]:
        if self._looks_like_v1(loaded_settings):
            normalized = deepcopy(loaded_settings)
        else:
            normalized = self._normalize_legacy_settings(loaded_settings)

        self._finalize_v1_shape(normalized)
        return normalized

    def _looks_like_v1(self, loaded_settings: dict[str, Any]) -> bool:
        if loaded_settings.get("version") in {1, 2}:
            return True

        v1_sections = {
            "site",
            "content",
            "theme",
            "build",
            "experimental",
            "extensions",
            "runtime",
            "integrations",
        }
        if any(section in loaded_settings for section in v1_sections):
            return True

        frontend = loaded_settings.get("frontend")
        if isinstance(frontend, dict) and (
            "targets" in frontend or "islands" in frontend
        ):
            return True

        return False

    def _normalize_legacy_settings(
        self, loaded_settings: dict[str, Any]
    ) -> dict[str, Any]:
        self.warnings.append(
            "Legacy config keys were detected and normalized into the v1 config shape."
        )

        frontend = loaded_settings.get("frontend", {})
        if not isinstance(frontend, dict):
            frontend = {}

        frontend_assets = frontend.get("assets", {})
        if not isinstance(frontend_assets, dict):
            frontend_assets = {}

        normalized: dict[str, Any] = {
            "version": 1,
            "site": {
                "name": loaded_settings.get("site_name", DEFAULT_SETTINGS["site"]["name"]),
                "description": loaded_settings.get(
                    "site_description", DEFAULT_SETTINGS["site"]["description"]
                ),
                "base_url": loaded_settings.get(
                    "base_url", DEFAULT_SETTINGS["site"]["base_url"]
                ),
                "author": loaded_settings.get(
                    "author", DEFAULT_SETTINGS["site"]["author"]
                ),
                "navigation": loaded_settings.get("navigation", []),
            },
            "content": {
                "source_directory": loaded_settings.get(
                    "source_directory", DEFAULT_SETTINGS["content"]["source_directory"]
                ),
                "data_dir": loaded_settings.get(
                    "data_dir", DEFAULT_SETTINGS["content"]["data_dir"]
                ),
                "models": {},
                "collections": deepcopy(loaded_settings.get("collections", {})),
            },
            "theme": {
                "name": frontend.get("theme", DEFAULT_SETTINGS["theme"]["name"]),
                "settings": "./theme.settings.yaml",
                "site_theme_dir": "./site-theme",
                "extra_css_urls": list(frontend_assets.get("css") or []),
                "extra_js_urls": list(frontend_assets.get("js") or []),
                "customizer": deepcopy(frontend.get("customizer", {})),
            },
            "build": {
                "output_directory": loaded_settings.get(
                    "output_directory", DEFAULT_SETTINGS["build"]["output_directory"]
                ),
                "asset_dirs": deepcopy(
                    loaded_settings.get("asset_dirs", DEFAULT_SETTINGS["build"]["asset_dirs"])
                ),
                "template_engine": loaded_settings.get(
                    "template_engine", DEFAULT_SETTINGS["build"]["template_engine"]
                ),
                "template_dirs": deepcopy(loaded_settings.get("template_dirs", [])),
                "log_level": loaded_settings.get(
                    "log_level", DEFAULT_SETTINGS["build"]["log_level"]
                ),
            },
            "extensions": deepcopy(DEFAULT_SETTINGS["extensions"]),
            "frontend": deepcopy(DEFAULT_SETTINGS["frontend"]),
            "runtime": deepcopy(DEFAULT_SETTINGS["runtime"]),
            "integrations": {},
            "plugins": deepcopy(loaded_settings.get("plugins", [])),
            "experimental": {
                "react": deepcopy(
                    loaded_settings.get(
                        "react", DEFAULT_SETTINGS["experimental"]["react"]
                    )
                ),
                "export_data": deepcopy(
                    frontend.get(
                        "export_data", DEFAULT_SETTINGS["experimental"]["export_data"]
                    )
                ),
                "tailwind": deepcopy(
                    frontend.get(
                        "tailwind", DEFAULT_SETTINGS["experimental"]["tailwind"]
                    )
                ),
            },
        }

        templates_by_type = loaded_settings.get("templates_by_type")
        if isinstance(templates_by_type, dict):
            normalized["content"]["templates_by_type"] = deepcopy(templates_by_type)
            self.warnings.append(
                "Legacy 'templates_by_type' is deprecated; prefer collection/layout mappings."
            )

        handled_keys = {
            "site_name",
            "site_description",
            "base_url",
            "author",
            "navigation",
            "source_directory",
            "data_dir",
            "collections",
            "frontend",
            "output_directory",
            "asset_dirs",
            "template_engine",
            "template_dirs",
            "log_level",
            "plugins",
            "react",
            "templates_by_type",
        }
        for key, value in loaded_settings.items():
            if key not in handled_keys:
                normalized[key] = deepcopy(value)

        return normalized

    def _finalize_v1_shape(self, normalized: dict[str, Any]) -> None:
        normalized.setdefault("version", 1)
        normalized.setdefault("site", {})
        normalized.setdefault("content", {})
        normalized.setdefault("theme", {})
        normalized.setdefault("build", {})
        normalized.setdefault("extensions", {})
        normalized.setdefault("frontend", {})
        normalized.setdefault("runtime", {})
        normalized.setdefault("integrations", {})
        normalized.setdefault("plugins", [])
        normalized.setdefault("experimental", {})

        site = normalized["site"]
        content = normalized["content"]
        theme = normalized["theme"]
        build = normalized["build"]
        extensions = normalized["extensions"]
        frontend = normalized["frontend"]
        runtime = normalized["runtime"]
        experimental = normalized["experimental"]

        if not isinstance(site, dict):
            normalized["site"] = deepcopy(DEFAULT_SETTINGS["site"])
            site = normalized["site"]
        if not isinstance(content, dict):
            normalized["content"] = deepcopy(DEFAULT_SETTINGS["content"])
            content = normalized["content"]
        if not isinstance(theme, dict):
            normalized["theme"] = deepcopy(DEFAULT_SETTINGS["theme"])
            theme = normalized["theme"]
        if not isinstance(build, dict):
            normalized["build"] = deepcopy(DEFAULT_SETTINGS["build"])
            build = normalized["build"]
        if not isinstance(extensions, dict):
            normalized["extensions"] = deepcopy(DEFAULT_SETTINGS["extensions"])
            extensions = normalized["extensions"]
        if not isinstance(frontend, dict):
            normalized["frontend"] = deepcopy(DEFAULT_SETTINGS["frontend"])
            frontend = normalized["frontend"]
        if not isinstance(runtime, dict):
            normalized["runtime"] = deepcopy(DEFAULT_SETTINGS["runtime"])
            runtime = normalized["runtime"]
        if not isinstance(experimental, dict):
            normalized["experimental"] = deepcopy(DEFAULT_SETTINGS["experimental"])
            experimental = normalized["experimental"]

        site.setdefault("navigation", [])
        content.setdefault(
            "source_directory", DEFAULT_SETTINGS["content"]["source_directory"]
        )
        content.setdefault("data_dir", DEFAULT_SETTINGS["content"]["data_dir"])
        content.setdefault("models", {})
        theme.setdefault("name", DEFAULT_SETTINGS["theme"]["name"])
        theme.setdefault("settings", DEFAULT_SETTINGS["theme"]["settings"])
        theme.setdefault("site_theme_dir", DEFAULT_SETTINGS["theme"]["site_theme_dir"])
        theme.setdefault("extra_css_urls", [])
        theme.setdefault("extra_js_urls", [])
        theme.setdefault("customizer", {})
        extensions.setdefault("enabled", [])
        extensions.setdefault("local_paths", ["./extensions"])
        frontend.setdefault("targets", [])
        frontend.setdefault("islands", [])
        runtime.setdefault("targets", [])
        build.setdefault(
            "output_directory", DEFAULT_SETTINGS["build"]["output_directory"]
        )
        build.setdefault("asset_dirs", deepcopy(DEFAULT_SETTINGS["build"]["asset_dirs"]))
        build.setdefault(
            "template_engine", DEFAULT_SETTINGS["build"]["template_engine"]
        )
        build.setdefault("template_dirs", [])
        build.setdefault("log_level", DEFAULT_SETTINGS["build"]["log_level"])
        experimental.setdefault(
            "react", deepcopy(DEFAULT_SETTINGS["experimental"]["react"])
        )
        experimental.setdefault(
            "export_data", deepcopy(DEFAULT_SETTINGS["experimental"]["export_data"])
        )
        experimental.setdefault(
            "tailwind", deepcopy(DEFAULT_SETTINGS["experimental"]["tailwind"])
        )

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
                default_prefix = "" if name == "pages" else raw_cfg.get("type", name)
                route["prefix"] = default_prefix

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

        react_cfg = experimental.get("react", {})
        frontend_targets = frontend.get("targets", [])
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
                    "export_subdir": react_cfg.get("export_subdir")
                    or react_cfg.get("collection", ""),
                    "base_path": react_cfg.get("base_path", ""),
                    "asset_prefix": react_cfg.get("asset_prefix", ""),
                }
            )
            self.warnings.append(
                "experimental.react is deprecated; a frontend.targets entry was synthesized."
            )
        frontend["targets"] = frontend_targets

    def _apply_compat_aliases(self) -> None:
        """Keep legacy callers working during the migration."""
        theme_name = self.get("theme.name", DEFAULT_SETTINGS["theme"]["name"])
        template_dirs = list(self.get("build.template_dirs", []))

        if not template_dirs:
            template_dirs = [f"./templates/{theme_name}/"]

        legacy_frontend = {
            "theme": theme_name,
            "assets": {
                "css": list(self.get("theme.extra_css_urls", [])),
                "js": list(self.get("theme.extra_js_urls", [])),
            },
            "tailwind": deepcopy(self.get("experimental.tailwind", {})),
            "export_data": deepcopy(self.get("experimental.export_data", {})),
            "customizer": deepcopy(self.get("theme.customizer", {})),
        }
        frontend_section = deepcopy(self.get("frontend", {}))
        if not isinstance(frontend_section, dict):
            frontend_section = {}
        for key, value in legacy_frontend.items():
            frontend_section.setdefault(key, value)

        self.settings["site_name"] = self.get("site.name")
        self.settings["site_description"] = self.get("site.description")
        self.settings["base_url"] = self.get("site.base_url")
        self.settings["author"] = self.get("site.author")
        self.settings["source_directory"] = self.get("content.source_directory")
        self.settings["data_dir"] = self.get("content.data_dir")
        self.settings["collections"] = deepcopy(self.get("content.collections", {}))
        self.settings["output_directory"] = self.get("build.output_directory")
        self.settings["template_engine"] = self.get("build.template_engine")
        self.settings["template_dirs"] = template_dirs
        self.settings["asset_dirs"] = deepcopy(self.get("build.asset_dirs", []))
        self.settings["log_level"] = self.get("build.log_level")
        self.settings["navigation"] = deepcopy(self.get("site.navigation", []))
        self.settings["react"] = deepcopy(self.get("experimental.react", {}))
        self.settings["frontend"] = frontend_section

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
