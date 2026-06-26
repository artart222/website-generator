"""Typed, immutable projection of the validated configuration.

The canonical configuration store is a single normalized nested mapping owned by
:class:`core.config.Config`. This module provides a *typed read view* over that
mapping so the SSG core can access the most-used settings with attribute access
and editor autocompletion instead of stringly-typed ``config.get("a.b.c")``
lookups.

There is intentionally ONE source of truth (the normalized mapping); these
dataclasses are derived from it at load time and never diverge.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SiteConfig:
    name: str
    description: str
    base_url: str
    author: str
    navigation: list[dict[str, Any]]


@dataclass(frozen=True)
class CollectionRoute:
    prefix: str = ""


@dataclass(frozen=True)
class CollectionIndex:
    enabled: bool = False
    layout: str = "collection"
    title: str = ""
    description: str = ""
    output_path: str = ""


@dataclass(frozen=True)
class CollectionConfig:
    name: str
    type: str
    model: str
    layout: str
    path: str | None
    route: CollectionRoute
    index: CollectionIndex
    defaults: dict[str, Any]
    raw: dict[str, Any]


@dataclass(frozen=True)
class ThemeConfig:
    name: str
    settings: str
    site_theme_dir: str
    extra_css_urls: list[str]
    extra_js_urls: list[str]
    customizer: dict[str, Any]


@dataclass(frozen=True)
class BuildConfig:
    output_directory: str
    asset_dirs: list[str]
    template_engine: str
    template_dirs: list[str]
    log_level: int
    strict: bool = True
    incremental: bool = False


@dataclass(frozen=True)
class ExportDataConfig:
    enabled: bool = False
    output_dir: str = "./output/data"
    include_collections: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TailwindConfig:
    enabled: bool = False
    input: str = "./styles/tailwind.input.css"
    output: str = "./styles/tailwind.css"
    config: str = "./tailwind.config.js"
    minify: bool = False


@dataclass(frozen=True)
class ExperimentalConfig:
    export_data: ExportDataConfig
    tailwind: TailwindConfig
    react: dict[str, Any]


@dataclass(frozen=True)
class AppConfig:
    """Typed, read-only view of the validated configuration."""

    version: int
    site: SiteConfig
    collections: dict[str, CollectionConfig]
    theme: ThemeConfig
    build: BuildConfig
    experimental: ExperimentalConfig


def _as_dict(value: Any) -> dict[str, Any]:
    return deepcopy(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return deepcopy(value) if isinstance(value, list) else []


def _build_collection(name: str, cfg: dict[str, Any]) -> CollectionConfig:
    route_cfg = cfg.get("route", {})
    route = CollectionRoute(prefix=str(route_cfg.get("prefix", "")) if isinstance(route_cfg, dict) else "")

    index_cfg = cfg.get("index", {})
    if not isinstance(index_cfg, dict):
        index_cfg = {}
    index = CollectionIndex(
        enabled=bool(index_cfg.get("enabled", False)),
        layout=str(index_cfg.get("layout", "collection")),
        title=str(index_cfg.get("title", "")),
        description=str(index_cfg.get("description", "")),
        output_path=str(index_cfg.get("output_path", "")),
    )

    return CollectionConfig(
        name=name,
        type=str(cfg.get("type", name)),
        model=str(cfg.get("model", name)),
        layout=str(cfg.get("layout", "document")),
        path=str(cfg["path"]) if cfg.get("path") else None,
        route=route,
        index=index,
        defaults=_as_dict(cfg.get("defaults")),
        raw=deepcopy(cfg),
    )


def build_app_config(settings: dict[str, Any]) -> AppConfig:
    """Project a normalized settings mapping into the typed :class:`AppConfig`."""
    site_cfg = _as_dict(settings.get("site"))
    content_cfg = _as_dict(settings.get("content"))
    theme_cfg = _as_dict(settings.get("theme"))
    build_cfg = _as_dict(settings.get("build"))
    experimental_cfg = _as_dict(settings.get("experimental"))

    collections_raw = content_cfg.get("collections", {})
    collections: dict[str, CollectionConfig] = {}
    if isinstance(collections_raw, dict):
        for name, cfg in collections_raw.items():
            if isinstance(cfg, dict):
                collections[str(name)] = _build_collection(str(name), cfg)

    export_data_cfg = _as_dict(experimental_cfg.get("export_data"))
    tailwind_cfg = _as_dict(experimental_cfg.get("tailwind"))

    return AppConfig(
        version=int(settings.get("version", 2)),
        site=SiteConfig(
            name=str(site_cfg.get("name", "")),
            description=str(site_cfg.get("description", "")),
            base_url=str(site_cfg.get("base_url", "")),
            author=str(site_cfg.get("author", "")),
            navigation=_as_list(site_cfg.get("navigation")),
        ),
        collections=collections,
        theme=ThemeConfig(
            name=str(theme_cfg.get("name", "minimal-blog")),
            settings=str(theme_cfg.get("settings", "./theme.settings.yaml")),
            site_theme_dir=str(theme_cfg.get("site_theme_dir", "./site-theme")),
            extra_css_urls=[str(u) for u in _as_list(theme_cfg.get("extra_css_urls"))],
            extra_js_urls=[str(u) for u in _as_list(theme_cfg.get("extra_js_urls"))],
            customizer=_as_dict(theme_cfg.get("customizer")),
        ),
        build=BuildConfig(
            output_directory=str(build_cfg.get("output_directory", "./output")),
            asset_dirs=[str(d) for d in _as_list(build_cfg.get("asset_dirs"))],
            template_engine=str(build_cfg.get("template_engine", "django")),
            template_dirs=[str(d) for d in _as_list(build_cfg.get("template_dirs"))],
            log_level=int(build_cfg.get("log_level", 20)),
            strict=bool(build_cfg.get("strict", True)),
            incremental=bool(build_cfg.get("incremental", False)),
        ),
        experimental=ExperimentalConfig(
            export_data=ExportDataConfig(
                enabled=bool(export_data_cfg.get("enabled", False)),
                output_dir=str(export_data_cfg.get("output_dir", "./output/data")),
                include_collections=[
                    str(c) for c in _as_list(export_data_cfg.get("include_collections"))
                ],
            ),
            tailwind=TailwindConfig(
                enabled=bool(tailwind_cfg.get("enabled", False)),
                input=str(tailwind_cfg.get("input", "./styles/tailwind.input.css")),
                output=str(tailwind_cfg.get("output", "./styles/tailwind.css")),
                config=str(tailwind_cfg.get("config", "./tailwind.config.js")),
                minify=bool(tailwind_cfg.get("minify", False)),
            ),
            react=_as_dict(experimental_cfg.get("react")),
        ),
    )
