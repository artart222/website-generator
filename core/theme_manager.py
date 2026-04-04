from __future__ import annotations

from copy import deepcopy
import logging
from pathlib import Path
from typing import Any

import yaml

from utils.fs_manager import FileSystemManager
from .config import Config


CORE_BLOCKS = ["hero", "rich_text", "feature_grid", "gallery", "cta", "faq"]
LEGACY_TEMPLATE_ROLE_MAP = {
    "base.html": "base",
    "post.html": "document",
    "blog-indexer.html": "collection",
    "404.html": "not_found",
}


class ThemeManager:
    """Loads theme manifests, settings, overrides, and generated theme CSS."""

    def __init__(self, config: Config, fs_manager: FileSystemManager) -> None:
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.fs_manager = fs_manager
        self.theme_name = str(self.config.get("theme.name", "minimal-blog"))
        self.theme_dir = Path("themes") / self.theme_name
        if not self.theme_dir.exists():
            package_theme_dir = Path(__file__).resolve().parent.parent / "themes" / self.theme_name
            if package_theme_dir.exists():
                self.theme_dir = package_theme_dir
        self.site_theme_dir = Path(self.config.get("theme.site_theme_dir", "./site-theme"))
        self.settings_path = Path(self.config.get("theme.settings", "./theme.settings.yaml"))
        self.manifest = self._load_theme_manifest()
        self.project_settings = self._load_project_settings()

    def _load_yaml_file(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}

        raw_content = self.fs_manager.read_file(path)
        parsed = yaml.safe_load(raw_content) or {}
        if not isinstance(parsed, dict):
            raise ValueError(f"YAML file must contain a mapping: {path}")
        return parsed

    def _load_theme_manifest(self) -> dict[str, Any]:
        manifest_path = self.theme_dir / "theme.yaml"
        if manifest_path.exists():
            manifest = self._load_yaml_file(manifest_path)
        else:
            self.logger.warning(
                "Theme manifest missing for '%s'. Falling back to legacy template layout.",
                self.theme_name,
            )
            manifest = {}

        manifest.setdefault("name", self.theme_name)
        manifest.setdefault("version", 1)
        manifest.setdefault("engine", "django")
        manifest.setdefault(
            "layouts",
            {
                "base": "layouts/base.html",
                "document": "layouts/document.html",
                "collection": "layouts/collection.html",
                "not_found": "layouts/404.html",
            },
        )
        manifest.setdefault("tokens", {})
        manifest.setdefault("presets", {})
        manifest.setdefault("supports", {"blocks": True})
        manifest.setdefault("assets", {})
        manifest.setdefault("blocks", {})
        manifest["blocks"].setdefault("core", deepcopy(CORE_BLOCKS))
        manifest["blocks"].setdefault("custom", [])

        assets = manifest["assets"]
        if not isinstance(assets, dict):
            assets = {}
            manifest["assets"] = assets
        assets.setdefault("styles", {"base": "styles/base.css"})
        assets.setdefault("static_dirs", ["assets"])

        return manifest

    def _load_project_settings(self) -> dict[str, Any]:
        settings = self._load_yaml_file(self.settings_path)
        settings.setdefault("preset", "default")
        settings.setdefault("tokens", {})
        settings.setdefault("presets", {})
        settings.setdefault("stylesheets", [])
        settings.setdefault("scripts", [])
        return settings

    def get_template_dirs(self) -> list[str]:
        template_dirs: list[str] = []
        for candidate in [self.site_theme_dir, self.theme_dir]:
            if candidate.exists():
                template_dirs.append(str(candidate))

        for legacy_dir in self.config.get("build.template_dirs", []):
            legacy_path = Path(legacy_dir)
            if legacy_path.exists():
                template_dirs.append(str(legacy_path))

        fallback_legacy_theme_dir = Path("templates") / self.theme_name
        if fallback_legacy_theme_dir.exists():
            template_dirs.append(str(fallback_legacy_theme_dir))

        deduped: list[str] = []
        for template_dir in template_dirs:
            if template_dir not in deduped:
                deduped.append(template_dir)
        return deduped

    def resolve_layout(self, requested_layout: str | None, page=None) -> str:
        if not requested_layout:
            requested_layout = "collection" if getattr(page, "is_collection_index", False) else "document"

        if requested_layout.endswith(".html"):
            requested_layout = LEGACY_TEMPLATE_ROLE_MAP.get(
                requested_layout, requested_layout
            )

        layouts = self.manifest.get("layouts", {})
        if isinstance(layouts, dict):
            return str(layouts.get(requested_layout, requested_layout))
        return str(requested_layout)

    def get_selected_preset(self) -> str:
        return str(self.project_settings.get("preset", "default"))

    def get_component_presets(self) -> dict[str, Any]:
        component_presets: dict[str, Any] = {}
        preset_name = self.get_selected_preset()
        preset_cfg = self.manifest.get("presets", {}).get(preset_name, {})
        if isinstance(preset_cfg, dict):
            component_presets = self._deep_merge_dicts(
                component_presets, deepcopy(preset_cfg.get("components", {}))
            )

        project_component_presets = self.project_settings.get("presets", {})
        if isinstance(project_component_presets, dict):
            allowed_variants = self._get_allowed_component_variants()
            filtered_project_component_presets: dict[str, Any] = {}

            for component_name, variant_name in project_component_presets.items():
                allowed_for_component = allowed_variants.get(component_name, set())

                if allowed_for_component and str(variant_name) not in allowed_for_component:
                    self.logger.warning(
                        "Ignoring incompatible theme preset override '%s: %s' for theme '%s'. Allowed variants: %s",
                        component_name,
                        variant_name,
                        self.theme_name,
                        ", ".join(sorted(allowed_for_component)),
                    )
                    continue

                filtered_project_component_presets[component_name] = deepcopy(
                    variant_name
                )

            component_presets = self._deep_merge_dicts(
                component_presets, filtered_project_component_presets
            )

        return component_presets

    def get_resolved_tokens(self) -> dict[str, Any]:
        tokens = deepcopy(self.manifest.get("tokens", {}))
        preset_name = self.get_selected_preset()
        preset_cfg = self.manifest.get("presets", {}).get(preset_name, {})

        if isinstance(preset_cfg, dict):
            tokens = self._deep_merge_dicts(
                tokens, deepcopy(preset_cfg.get("tokens", {}))
            )

        project_tokens = self.project_settings.get("tokens", {})
        if isinstance(project_tokens, dict):
            tokens = self._deep_merge_dicts(tokens, deepcopy(project_tokens))

        return tokens

    def get_layout_options(self, page) -> dict[str, Any]:
        layout_options: dict[str, Any] = {}
        if isinstance(page.collection_config, dict):
            defaults = page.collection_config.get("defaults", {})
            if isinstance(defaults, dict):
                collection_layout_options = defaults.get("layout_options", {})
                if isinstance(collection_layout_options, dict):
                    layout_options = self._deep_merge_dicts(
                        layout_options, deepcopy(collection_layout_options)
                    )

        if isinstance(page.layout_options, dict):
            layout_options = self._deep_merge_dicts(
                layout_options, deepcopy(page.layout_options)
            )

        return layout_options

    def get_stylesheets(self) -> list[str]:
        stylesheets = ["/styles/theme-base.css", "/styles/theme.css"]

        if (self.site_theme_dir / "styles" / "overrides.css").exists():
            stylesheets.append("/styles/theme-overrides.css")

        stylesheets.extend(self.project_settings.get("stylesheets", []))
        stylesheets.extend(self.config.get("theme.extra_css_urls", []))
        return stylesheets

    def get_scripts(self) -> list[str]:
        scripts = []
        scripts.extend(self.project_settings.get("scripts", []))
        scripts.extend(self.config.get("theme.extra_js_urls", []))
        return scripts

    def get_theme_context(self) -> dict[str, Any]:
        return {
            "theme_name": self.theme_name,
            "theme_manifest": self.manifest,
            "theme_settings": self.project_settings,
            "theme_tokens": self.get_resolved_tokens(),
            "theme_component_presets": self.get_component_presets(),
            "core_blocks": deepcopy(CORE_BLOCKS),
        }

    def prepare_theme_output(self, output_dir: Path) -> None:
        styles_dir = output_dir / "styles"
        self.fs_manager.create_directory(styles_dir)

        base_style_rel = (
            self.manifest.get("assets", {})
            .get("styles", {})
            .get("base", "styles/base.css")
        )
        base_style_source = self.theme_dir / str(base_style_rel)
        base_style_dest = styles_dir / "theme-base.css"

        if base_style_source.exists():
            self.fs_manager.copy_file(base_style_source, base_style_dest)
        else:
            self.fs_manager.write_file(base_style_dest, "")

        generated_theme_css = self._render_theme_css()
        self.fs_manager.write_file(styles_dir / "theme.css", generated_theme_css)

        override_source = self.site_theme_dir / "styles" / "overrides.css"
        if override_source.exists():
            self.fs_manager.copy_file(override_source, styles_dir / "theme-overrides.css")

        static_dirs = self.manifest.get("assets", {}).get("static_dirs", [])
        if not isinstance(static_dirs, list):
            static_dirs = ["assets"]

        for static_dir_name in static_dirs:
            theme_static_dir = self.theme_dir / str(static_dir_name)
            if theme_static_dir.exists():
                self.fs_manager.copy_directory(
                    theme_static_dir, output_dir / Path(static_dir_name).name, exist_ok=True
                )

        override_assets_dir = self.site_theme_dir / "assets"
        if override_assets_dir.exists():
            self.fs_manager.copy_directory(
                override_assets_dir, output_dir / "assets", exist_ok=True
            )

    def render_blocks(
        self,
        blocks: list[dict[str, Any]],
        template_engine,
        base_context: dict[str, Any],
    ) -> str:
        if not blocks:
            return ""

        rendered_blocks: list[str] = []
        for block in blocks:
            if not isinstance(block, dict):
                continue

            block_type = str(block.get("type", "")).strip()
            if not block_type:
                continue

            template_name = self._resolve_block_template(block_type)
            block_context = dict(base_context)
            block_content = {
                "title": "",
                "text": "",
                "html": "",
                "eyebrow": "",
                "actions": [],
                "action": {},
            }
            raw_block_content = block.get("content", {}) or {}
            if isinstance(raw_block_content, dict):
                block_content = self._deep_merge_dicts(
                    block_content, deepcopy(raw_block_content)
                )
            block_context["block"] = {
                "type": block_type,
                "variant": block.get("variant", ""),
                "settings": block.get("settings", {}) or {},
                "content": block_content,
                "items": block.get("items", []) or [],
            }

            rendered_blocks.append(template_engine.render(template_name, block_context))

        return "\n".join(rendered_blocks)

    def _resolve_block_template(self, block_type: str) -> str:
        if "/" in block_type:
            namespace, custom_name = block_type.split("/", 1)
            return f"blocks/{namespace}/{custom_name}.html"
        return f"blocks/{block_type}.html"

    def _render_theme_css(self) -> str:
        tokens = self.get_resolved_tokens()
        css_lines = [":root {"]
        for variable_name, value in self._flatten_tokens(tokens):
            css_lines.append(f"  --{variable_name}: {value};")
        css_lines.append("}")
        return "\n".join(css_lines) + "\n"

    def _flatten_tokens(
        self, values: dict[str, Any], prefix: str = ""
    ) -> list[tuple[str, Any]]:
        flat_items: list[tuple[str, Any]] = []
        for key, value in values.items():
            safe_key = str(key).replace("_", "-")
            variable_name = f"{prefix}-{safe_key}" if prefix else safe_key
            if isinstance(value, dict):
                flat_items.extend(self._flatten_tokens(value, variable_name))
            else:
                flat_items.append((variable_name, value))
        return flat_items

    def _get_allowed_component_variants(self) -> dict[str, set[str]]:
        allowed_variants: dict[str, set[str]] = {}
        manifest_presets = self.manifest.get("presets", {})
        if not isinstance(manifest_presets, dict):
            return allowed_variants

        for preset_cfg in manifest_presets.values():
            if not isinstance(preset_cfg, dict):
                continue

            components = preset_cfg.get("components", {})
            if not isinstance(components, dict):
                continue

            for component_name, variant_name in components.items():
                if variant_name is None:
                    continue
                allowed_variants.setdefault(str(component_name), set()).add(
                    str(variant_name)
                )

        return allowed_variants

    def _deep_merge_dicts(
        self, base: dict[str, Any], updates: dict[str, Any]
    ) -> dict[str, Any]:
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key] = self._deep_merge_dicts(base[key], value)
            else:
                base[key] = value
        return base
