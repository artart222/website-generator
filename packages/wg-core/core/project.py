from __future__ import annotations

import logging
from typing import Any, Callable

from engines.base_engine import TemplateEngine
from engines.factory import create_template_engine
from utils.fs_manager import FileSystemManager
from wg_contracts.ports import FileSystemPort
from .build_cache import BuildCache, compute_build_signature
from .build_context import BuildContext
from .build_pipeline import BuildPipeline
from .config import Config
from .exporting import JsonExporter
from .extension_manager import ExtensionManager
from .frontend_manager import FrontendManager
from .plugin_manager import PluginManager
from .rendering import PageContextBuilder, TemplateResolver
from .router import Router
from .runtime_manager import RuntimeManager
from .site import Site
from .theme_manager import ThemeManager


class Project:
    """Facade that wires the build subsystem together and runs the pipeline.

    All build work is performed by discrete collaborators operating on a shared
    :class:`~core.build_context.BuildContext`; this class only constructs them
    (the composition root for a build) and exposes a small, stable surface.
    """

    def __init__(
        self,
        config: Config,
        *,
        fs_manager: FileSystemPort | None = None,
        template_engine_factory: Callable[[str, list[str]], TemplateEngine] = create_template_engine,
    ):
        self.logger = logging.getLogger(__name__)
        self.config: Config = config
        self.strict: bool = bool(config.get("build.strict", True))
        self.fs_manager: FileSystemPort = fs_manager or FileSystemManager()

        self.extension_manager = ExtensionManager(self.config, self.fs_manager)
        self.extension_manager.detect_and_load_extensions()
        self.site: Site = Site(self.config)
        self.router = Router(self.config)
        self.theme_manager = ThemeManager(self.config, self.fs_manager)
        self.frontend_manager = FrontendManager(
            self.config, self.fs_manager, self.extension_manager
        )
        self.runtime_manager = RuntimeManager(
            self.config, self.fs_manager, self.extension_manager, strict=self.strict
        )
        self.plugin_manager: PluginManager = PluginManager(
            self.config, self.site, strict=self.strict
        )
        self.plugin_manager.detect_and_load_plugins()

        self.plugin_manager.run_hook(
            "after_config_loaded",
            site=self.site,
            config=self.config,
            fs_manager=self.fs_manager,
            extension_manager=self.extension_manager,
        )

        template_dirs = (
            self.theme_manager.get_template_dirs()
            + self.extension_manager.get_template_dirs()
        )
        deduped_template_dirs: list[str] = []
        for template_dir in template_dirs:
            if template_dir not in deduped_template_dirs:
                deduped_template_dirs.append(template_dir)

        self.template_engine: TemplateEngine = template_engine_factory(
            self.config.get("build.template_engine"),
            deduped_template_dirs,
        )

        self.incremental: bool = bool(config.get("build.incremental", False))
        build_cache = self._create_build_cache() if self.incremental else None

        self.context = BuildContext(
            config=self.config,
            fs_manager=self.fs_manager,
            site=self.site,
            router=self.router,
            theme_manager=self.theme_manager,
            plugin_manager=self.plugin_manager,
            extension_manager=self.extension_manager,
            frontend_manager=self.frontend_manager,
            runtime_manager=self.runtime_manager,
            template_engine=self.template_engine,
            strict=self.strict,
            incremental=self.incremental,
            build_cache=build_cache,
            project=self,
        )
        self.pipeline = BuildPipeline(self.context)

    def _create_build_cache(self) -> BuildCache:
        from pathlib import Path

        output_dir = Path(self.config.get("build.output_directory"))
        signature = compute_build_signature(
            {
                "theme_tokens": self.theme_manager.get_resolved_tokens(),
                "site": self.config.get("site", {}),
                "template_engine": self.config.get("build.template_engine"),
                "plugins": self.config.get("plugins", []),
            }
        )
        return BuildCache(output_dir, signature)

    def build(self) -> None:
        self.pipeline.run()

    def get_template_engine(self) -> TemplateEngine:
        return self.template_engine

    # -- thin delegations kept for callers/tests --------------------------

    @property
    def runtime_catalog_snapshot(self) -> dict[str, Any] | None:
        return self.context.runtime_catalog_snapshot

    @runtime_catalog_snapshot.setter
    def runtime_catalog_snapshot(self, value: dict[str, Any] | None) -> None:
        self.context.runtime_catalog_snapshot = value

    def _build_page_context(
        self, page, header: str, navigation_items: list[dict]
    ) -> dict:
        return PageContextBuilder(self.context).build(page, header, navigation_items)

    def _resolve_template_name(self, page) -> str:
        return TemplateResolver(self.context).resolve(page)

    def _export_json_data(self) -> None:
        JsonExporter(self.context).export()

    def _discover_and_load_pages(self) -> None:
        self.pipeline.discoverer.discover()

    def _apply_content_models(self, *, only_missing: bool = False) -> None:
        self.pipeline._apply_content_models(only_missing=only_missing)

    def _assign_routes(self) -> None:
        self.pipeline._assign_routes()
