from __future__ import annotations

import json
import logging
import os
import shutil
from copy import deepcopy
from pathlib import Path

import yaml

from engines.base_engine import TemplateEngine
from engines.factory import create_template_engine
from processor.factory import _PROCESSOR_MAP, create_content_processor
from processor.react_processor import build_react_section
from processor.tailwind_processor import build_tailwind
from utils.fs_manager import FileSystemManager
from .config import Config
from .page import Page
from .plugin_manager import PluginManager
from .router import Router
from .site import Site
from .theme_manager import ThemeManager

supported_extensions = list(_PROCESSOR_MAP.keys())


class Project:
    """Main build orchestrator."""

    def __init__(self, config: Config):
        self.logger = logging.getLogger(__name__)
        self.config: Config = config
        self.fs_manager: FileSystemManager = FileSystemManager()
        self.site: Site = Site(self.config)
        self.router = Router(self.config)
        self.theme_manager = ThemeManager(self.config, self.fs_manager)
        self.plugin_manager: PluginManager = PluginManager(self.config, self.site)
        self.plugin_manager.detect_and_load_plugins()

        self.plugin_manager.run_hook(
            "after_config_loaded",
            site=self.site,
            config=self.config,
            fs_manager=self.fs_manager,
        )

        self.template_engine: TemplateEngine = create_template_engine(
            self.config.get("build.template_engine", self.config.get("template_engine")),
            self.theme_manager.get_template_dirs(),
        )

    def build(self) -> None:
        self.plugin_manager.run_hook(
            "before_build",
            site=self.site,
            config=self.config,
            fs_manager=self.fs_manager,
        )

        self.logger.info("Build process started.")
        self._prepare_output_dir()

        self._discover_and_load_pages()
        self._load_site_data()
        self._assign_routes()

        self.plugin_manager.run_hook(
            "after_collections_loaded",
            site=self.site,
            config=self.config,
            fs_manager=self.fs_manager,
        )
        self.plugin_manager.run_hook(
            "after_pages_discovered",
            site=self.site,
            config=self.config,
            fs_manager=self.fs_manager,
        )

        self._assign_routes()
        self.plugin_manager.run_hook(
            "after_routes_built",
            site=self.site,
            config=self.config,
            fs_manager=self.fs_manager,
        )

        self._render_pages()
        self._export_json_data()
        build_react_section(self.config, self.fs_manager, self.logger)
        self._build_tailwind()
        self._copy_assets()

        self.plugin_manager.run_hook(
            "after_build",
            site=self.site,
            config=self.config,
            fs_manager=self.fs_manager,
        )

        self.logger.info("Build process finished successfully.")

    def _prepare_output_dir(self) -> None:
        output_dir = Path(
            self.config.get("build.output_directory", self.config.get("output_directory"))
        )
        resolved_output_dir = output_dir.resolve()
        project_root = Path.cwd().resolve()

        if resolved_output_dir == project_root:
            raise ValueError(
                f"Refusing to use the project root as the output directory: {resolved_output_dir}"
            )
        if output_dir.exists() and output_dir.is_file():
            raise FileExistsError(f"Output path is a file, not a directory: {output_dir}")

        self.fs_manager.create_directory(output_dir)
        for child in output_dir.iterdir():
            if child.name == ".git":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

    def get_template_engine(self) -> TemplateEngine:
        return self.template_engine

    def _discover_and_load_pages(self) -> None:
        self.logger.info("Discovering and loading site content...")

        collections = self.config.get("content.collections", self.config.get("collections"))
        output_dir = Path(
            self.config.get("build.output_directory", self.config.get("output_directory"))
        )

        if isinstance(collections, dict) and collections:
            collection_items: list[tuple[str, dict, Path]] = []
            for name, cfg in collections.items():
                if not isinstance(cfg, dict):
                    continue
                path_value = cfg.get("path")
                if not path_value:
                    continue
                collection_items.append((name, cfg, Path(path_value)))

            collection_items.sort(
                key=lambda item: len(item[2].resolve().parts), reverse=True
            )

            seen_paths: set[Path] = set()
            for name, cfg, collection_path in collection_items:
                if not collection_path.exists():
                    self.logger.warning("Collection path does not exist: %s", collection_path)
                    continue

                page_filepaths = self.fs_manager.list_files(collection_path, recursive=True)
                for path in page_filepaths:
                    if path in seen_paths:
                        continue
                    seen_paths.add(path)

                    ext = os.path.splitext(path)[1].lstrip(".").lower()
                    if ext not in supported_extensions:
                        continue

                    page = Page(path, self.config, self.fs_manager)
                    page.collection = name
                    page.collection_config = cfg
                    page.set_route_prefix(cfg.get("route", {}).get("prefix", ""))

                    self.plugin_manager.run_hook(
                        "before_page_parsed",
                        site=self.site,
                        config=self.config,
                        fs_manager=self.fs_manager,
                        page=page,
                    )

                    processor = create_content_processor(ext)
                    page.load(processor)
                    self._apply_collection_defaults(page, cfg)

                    if page.draft:
                        self.logger.info("Skipping draft page: %s", page.source_filepath)
                        continue

                    self.site.add_page(page)

                    self.plugin_manager.run_hook(
                        "after_document_loaded",
                        site=self.site,
                        config=self.config,
                        fs_manager=self.fs_manager,
                        page=page,
                    )
                    self.plugin_manager.run_hook(
                        "after_page_parsed",
                        site=self.site,
                        config=self.config,
                        fs_manager=self.fs_manager,
                        page=page,
                    )
        else:
            content_path = Path(
                self.config.get("content.source_directory", self.config.get("source_directory"))
            )
            if not content_path.exists():
                self.logger.warning("Source directory does not exist: %s", content_path)
                return

            page_filepaths = self.fs_manager.list_files(content_path, recursive=True)
            for path in page_filepaths:
                ext = os.path.splitext(path)[1].lstrip(".").lower()
                if ext not in supported_extensions:
                    continue

                page = Page(path, self.config, self.fs_manager)
                self.plugin_manager.run_hook(
                    "before_page_parsed",
                    site=self.site,
                    config=self.config,
                    fs_manager=self.fs_manager,
                    page=page,
                )

                processor = create_content_processor(ext)
                page.load(processor)
                if page.draft:
                    continue

                if not page.get_output_path():
                    page.calculate_output_path(output_dir)

                self.site.add_page(page)
                self.plugin_manager.run_hook(
                    "after_document_loaded",
                    site=self.site,
                    config=self.config,
                    fs_manager=self.fs_manager,
                    page=page,
                )
                self.plugin_manager.run_hook(
                    "after_page_parsed",
                    site=self.site,
                    config=self.config,
                    fs_manager=self.fs_manager,
                    page=page,
                )

    def _apply_collection_defaults(self, page: Page, collection_cfg: dict) -> None:
        page.set_route_prefix(collection_cfg.get("route", {}).get("prefix", ""))

        defaults = collection_cfg.get("defaults", {})
        if not isinstance(defaults, dict):
            defaults = {}

        if not page.page_type:
            collection_type = collection_cfg.get("type") or defaults.get("type")
            if collection_type:
                page.set_page_type(str(collection_type))

        if not page.layout:
            layout = (
                page.metadata.get("layout")
                or collection_cfg.get("layout")
                or defaults.get("layout")
                or page.metadata.get("template")
            )
            if layout:
                page.layout = str(layout[0] if isinstance(layout, list) else layout)

        if not page.layout_options and isinstance(defaults.get("layout_options"), dict):
            page.layout_options = deepcopy(defaults.get("layout_options", {}))

    def _assign_routes(self) -> None:
        for page in self.site.pages:
            self.router.assign(page)

    def _render_pages(self) -> None:
        self.logger.info("Rendering pages...")
        navigation_items = self.site.build_navigation()
        header = self.site.populate_header()

        for page in self.site.pages:
            self.plugin_manager.run_hook(
                "before_page_rendered",
                site=self.site,
                config=self.config,
                fs_manager=self.fs_manager,
                page=page,
            )

            context = self._build_page_context(page, header, navigation_items)
            template_name = self._resolve_template_name(page)
            rendered_html = self.template_engine.render(template_name, context)
            output_path = page.get_output_path()
            if output_path is None:
                raise RuntimeError(f"No output path assigned for page '{page.title}'")

            self.fs_manager.write_file(output_path, rendered_html)
            self.logger.debug(
                "Rendered page: %s -> %s", page.source_filepath, page.get_output_path()
            )

            self.plugin_manager.run_hook(
                "after_page_rendered",
                site=self.site,
                config=self.config,
                fs_manager=self.fs_manager,
                page=page,
            )

    def _build_page_context(
        self, page: Page, header: str, navigation_items: list[dict]
    ) -> dict:
        stylesheets = self.theme_manager.get_stylesheets()
        scripts = self.theme_manager.get_scripts()
        layout_options = self.theme_manager.get_layout_options(page)
        theme_context = self.theme_manager.get_theme_context()

        css_injections = self.plugin_manager.run_hook_collect(
            "inject_css",
            site=self.site,
            config=self.config,
            fs_manager=self.fs_manager,
            page=page,
        )
        for injected in css_injections:
            if isinstance(injected, str):
                stylesheets.append(injected)
            elif isinstance(injected, (list, tuple)):
                stylesheets.extend(injected)

        js_injections = self.plugin_manager.run_hook_collect(
            "inject_js",
            site=self.site,
            config=self.config,
            fs_manager=self.fs_manager,
            page=page,
        )
        for injected in js_injections:
            if isinstance(injected, str):
                scripts.append(injected)
            elif isinstance(injected, (list, tuple)):
                scripts.extend(injected)

        base_context = page.get_context(
            header=header,
            site=self.site,
            stylesheets=stylesheets,
            scripts=scripts,
            navigation_items=navigation_items,
            theme_context=theme_context,
            layout_options=layout_options,
        )
        rendered_blocks = self.theme_manager.render_blocks(
            page.blocks, self.template_engine, base_context
        )
        context = page.get_context(
            header=header,
            site=self.site,
            stylesheets=stylesheets,
            scripts=scripts,
            navigation_items=navigation_items,
            theme_context=theme_context,
            rendered_blocks=rendered_blocks,
            layout_options=layout_options,
        )

        for update in self.plugin_manager.run_hook_collect(
            "modify_context",
            context=context,
            site=self.site,
            config=self.config,
            fs_manager=self.fs_manager,
            page=page,
        ):
            if isinstance(update, dict):
                context.update(update)

        for update in self.plugin_manager.run_hook_collect(
            "modify_template_context",
            context=context,
            site=self.site,
            config=self.config,
            fs_manager=self.fs_manager,
            page=page,
        ):
            if isinstance(update, dict):
                context.update(update)

        return context

    def _resolve_template_name(self, page: Page) -> str:
        requested_layout = page.layout
        if not requested_layout and isinstance(page.collection_config, dict):
            requested_layout = (
                page.collection_config.get("layout")
                or page.collection_config.get("defaults", {}).get("layout")
            )

        if page.is_not_found_page():
            requested_layout = "not_found"
        elif page.is_collection_index and not requested_layout:
            requested_layout = "collection"

        if not requested_layout:
            templates_by_type = self.config.get("content.templates_by_type", {})
            if isinstance(templates_by_type, dict):
                requested_layout = templates_by_type.get(page.page_type)

        if not requested_layout:
            requested_layout = "document"

        return self.theme_manager.resolve_layout(str(requested_layout), page)

    def _build_tailwind(self) -> None:
        build_tailwind(self.config)

    def _load_site_data(self) -> None:
        data_dir_value = self.config.get("content.data_dir", self.config.get("data_dir"))
        if not data_dir_value:
            return

        data_dir = Path(data_dir_value)
        if not data_dir.exists():
            self.logger.info("Data directory does not exist: %s", data_dir)
            return

        data_files = self.fs_manager.list_files(
            data_dir, recursive=True, extensions=[".json", ".yaml", ".yml"]
        )

        data: dict = {}
        for data_file in data_files:
            try:
                raw_content = self.fs_manager.read_file(data_file)
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

        self.site.set_data(data)

    def _export_json_data(self) -> None:
        export_data = self.config.get(
            "experimental.export_data",
            self.config.get("frontend", {}).get("export_data", {}),
        )
        if not isinstance(export_data, dict) or not export_data.get("enabled", False):
            return

        output_dir = Path(
            self.config.get("build.output_directory", self.config.get("output_directory"))
        )
        data_dir = Path(export_data.get("output_dir", "./output/data"))
        include_collections = export_data.get("include_collections")
        filter_collections = (
            isinstance(include_collections, list) and len(include_collections) > 0
        )

        site_payload: dict = {
            "site": {
                "name": self.config.get("site.name", ""),
                "description": self.config.get("site.description", ""),
                "base_url": self.config.get("site.base_url", ""),
            },
            "pages": [],
        }

        for page in self.site.pages:
            if filter_collections and page.collection not in include_collections:
                continue

            output_path = page.get_output_path()
            if not output_path:
                continue

            try:
                rel_output_path = output_path.relative_to(output_dir)
            except ValueError:
                rel_output_path = Path(output_path.name)

            if rel_output_path.name == "index.html":
                json_rel_path = rel_output_path.parent / "page.json"
            else:
                json_rel_path = rel_output_path.with_suffix(".json")
            json_output_path = data_dir / json_rel_path

            page_payload = {
                "title": page.title,
                "slug": page.slug,
                "type": page.page_type,
                "collection": page.collection,
                "abs_url": page.abs_url,
                "root_rel_url": page.root_rel_url,
                "metadata": page.metadata,
                "content_html": page.processed_content,
                "blocks": page.blocks,
                "layout": page.layout,
            }

            self.fs_manager.write_file(
                json_output_path, json.dumps(page_payload, ensure_ascii=False, indent=2)
            )

            try:
                data_rel_dir = data_dir.relative_to(output_dir)
                json_path = data_rel_dir / json_rel_path
            except ValueError:
                json_path = json_output_path

            site_payload["pages"].append(
                {
                    "title": page.title,
                    "slug": page.slug,
                    "type": page.page_type,
                    "collection": page.collection,
                    "url": page.abs_url,
                    "root_rel_url": page.root_rel_url,
                    "json_path": str(json_path).replace(os.sep, "/"),
                }
            )

        site_index_path = data_dir / "site.json"
        self.fs_manager.write_file(
            site_index_path, json.dumps(site_payload, ensure_ascii=False, indent=2)
        )

    def _copy_assets(self) -> None:
        output_dir = Path(
            self.config.get("build.output_directory", self.config.get("output_directory"))
        )
        self.theme_manager.prepare_theme_output(output_dir)

        asset_dirs = list(self.config.get("build.asset_dirs", self.config.get("asset_dirs", [])))
        if "./styles" not in asset_dirs:
            asset_dirs.insert(0, "./styles")

        for asset_dir_value in asset_dirs:
            asset_dir = Path(asset_dir_value)
            if asset_dir.exists():
                self.fs_manager.copy_directory(
                    asset_dir, output_dir / asset_dir.name, exist_ok=True
                )
                self.logger.info("Copied asset directory: %s", asset_dir)
            else:
                self.logger.warning("Asset directory does not exist: %s", asset_dir)
