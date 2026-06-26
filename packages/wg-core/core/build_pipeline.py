"""The build pipeline: an explicit, ordered sequence of build steps.

This replaces the former ``Project.build()`` god method. Each step is a named,
single-responsibility callable operating on a shared :class:`BuildContext`, so
the build order is explicit and individually testable instead of being an
800-line method whose phase ordering is implicit.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import yaml

from processor.tailwind_processor import build_tailwind
from .build_context import BuildContext
from .content_models import ContentModelError
from .assets import AssetCopier, OutputPreparer
from .discovery import ContentDiscoverer
from .exporting import JsonExporter
from .rendering import PageRenderer


@dataclass
class BuildStep:
    """A named build step. ``run`` mutates the shared context."""

    name: str
    run: Callable[[], None]


class BuildPipeline:
    """Runs the ordered build steps against a shared context."""

    def __init__(self, ctx: BuildContext) -> None:
        self.ctx = ctx
        self.logger = logging.getLogger("core.build")
        self.discoverer = ContentDiscoverer(ctx)
        self.renderer = PageRenderer(ctx)
        self.exporter = JsonExporter(ctx)
        self.output_preparer = OutputPreparer(ctx)
        self.asset_copier = AssetCopier(ctx)
        self.steps = self._build_steps()

    def _build_steps(self) -> list[BuildStep]:
        return [
            BuildStep("before_build_hooks", self._before_build_hooks),
            BuildStep("prepare_output_dir", self.output_preparer.prepare),
            BuildStep("fetch_runtime_catalog", self._fetch_runtime_catalog),
            BuildStep("discover_pages", self.discoverer.discover),
            BuildStep("apply_content_models", self._apply_content_models_all),
            BuildStep("after_pages_modeled_hook", self._after_pages_modeled_hook),
            BuildStep("load_site_data", self._load_site_data),
            BuildStep("assign_routes_initial", self._assign_routes),
            BuildStep("after_collections_loaded_hooks", self._after_collections_loaded_hooks),
            BuildStep("apply_content_models_generated", self._apply_content_models_generated),
            BuildStep("assign_routes_final", self._assign_routes),
            BuildStep("after_routes_built_hooks", self._after_routes_built_hooks),
            BuildStep("render_pages", self.renderer.render_all),
            BuildStep("export_json", self._export_json),
            BuildStep("build_frontend_targets", self._build_frontend_targets),
            BuildStep("emit_runtime_manifest", self._emit_runtime_manifest),
            BuildStep("build_tailwind", self._build_tailwind),
            BuildStep("copy_assets", self.asset_copier.copy),
            BuildStep("after_build_hooks", self._after_build_hooks),
        ]

    def run(self) -> None:
        self.logger.info("Build process started.")
        for step in self.steps:
            self.logger.debug("Build step: %s", step.name)
            step.run()
        self.logger.info("Build process finished successfully.")

    # -- hook steps --------------------------------------------------------

    def _before_build_hooks(self) -> None:
        ctx = self.ctx
        ctx.extension_manager.run_build_hook(
            "before_build", project=self.ctx.project, site=ctx.site, config=ctx.config
        )
        ctx.plugin_manager.run_hook(
            "before_build", site=ctx.site, config=ctx.config, fs_manager=ctx.fs_manager
        )

    def _after_pages_modeled_hook(self) -> None:
        self.ctx.extension_manager.run_build_hook(
            "after_pages_modeled", project=self.ctx.project, site=self.ctx.site, config=self.ctx.config
        )

    def _after_collections_loaded_hooks(self) -> None:
        ctx = self.ctx
        ctx.plugin_manager.run_hook(
            "after_collections_loaded", site=ctx.site, config=ctx.config, fs_manager=ctx.fs_manager
        )
        ctx.plugin_manager.run_hook(
            "after_pages_discovered", site=ctx.site, config=ctx.config, fs_manager=ctx.fs_manager
        )

    def _after_routes_built_hooks(self) -> None:
        ctx = self.ctx
        ctx.plugin_manager.run_hook(
            "after_routes_built", site=ctx.site, config=ctx.config, fs_manager=ctx.fs_manager
        )
        ctx.extension_manager.run_build_hook(
            "after_routes_built", project=self.ctx.project, site=ctx.site, config=ctx.config
        )

    def _after_build_hooks(self) -> None:
        ctx = self.ctx
        ctx.plugin_manager.run_hook(
            "after_build", site=ctx.site, config=ctx.config, fs_manager=ctx.fs_manager
        )
        ctx.extension_manager.run_build_hook(
            "after_build", project=self.ctx.project, site=ctx.site, config=ctx.config
        )

    # -- work steps --------------------------------------------------------

    def _fetch_runtime_catalog(self) -> None:
        ctx = self.ctx
        snapshot_data, output_path = ctx.runtime_manager.fetch_catalog_snapshot()
        if snapshot_data is None:
            self.logger.debug("Runtime catalog snapshot fetching is disabled or not configured.")
            return
        ctx.runtime_catalog_snapshot = snapshot_data
        if output_path is not None:
            self.logger.info("Runtime catalog snapshot saved to %s", output_path)

    def _apply_content_models_all(self) -> None:
        self._apply_content_models(only_missing=False)

    def _apply_content_models_generated(self) -> None:
        self._apply_content_models(only_missing=True)

    def _apply_content_models(self, *, only_missing: bool) -> None:
        ctx = self.ctx
        for page in ctx.site.pages:
            if only_missing and page.model_name:
                continue
            try:
                ctx.extension_manager.model_registry.apply_to_page(page)
            except ContentModelError as exc:
                raise ContentModelError(str(exc)) from exc

    def _assign_routes(self) -> None:
        for page in self.ctx.site.pages:
            self.ctx.router.assign(page)

    def _load_site_data(self) -> None:
        ctx = self.ctx
        data_dir_value = ctx.config.get("content.data_dir")
        if not data_dir_value:
            return

        data_dir = Path(data_dir_value)
        if not data_dir.exists():
            self.logger.info("Data directory does not exist: %s", data_dir)
            return

        data_files = ctx.fs_manager.list_files(
            data_dir, recursive=True, extensions=[".json", ".yaml", ".yml"]
        )

        data: dict = {}
        for data_file in data_files:
            try:
                raw_content = ctx.fs_manager.read_file(data_file)
                if data_file.suffix.lower() == ".json":
                    parsed = json.loads(raw_content)
                else:
                    parsed = yaml.safe_load(raw_content)

                rel_path = data_file.relative_to(data_dir).with_suffix("")
                parts = rel_path.parts
                cursor = data
                for part in parts[:-1]:
                    cursor = cursor.setdefault(part, {})
                cursor[parts[-1]] = parsed
            except Exception as exc:
                self.logger.error(
                    "Failed to load data file %s: %s", data_file, exc, exc_info=True
                )
                if ctx.strict:
                    raise

        ctx.site.set_data(data)

    def _export_json(self) -> None:
        self.exporter.export()
        self.ctx.extension_manager.run_build_hook(
            "after_json_export", project=self.ctx.project, site=self.ctx.site, config=self.ctx.config
        )

    def _build_frontend_targets(self) -> None:
        ctx = self.ctx
        ctx.frontend_manager.build_targets(
            runtime_public_config=ctx.runtime_manager.build_public_config()
        )
        ctx.extension_manager.run_build_hook(
            "after_frontend_targets", project=self.ctx.project, site=ctx.site, config=ctx.config
        )

    def _emit_runtime_manifest(self) -> None:
        ctx = self.ctx
        ctx.runtime_manager.emit_manifest()
        ctx.extension_manager.run_build_hook(
            "after_runtime_manifest", project=self.ctx.project, site=ctx.site, config=ctx.config
        )

    def _build_tailwind(self) -> None:
        build_tailwind(self.ctx.config)
