from .site import Site
from .config import Config
from .page import Page
from engines.base_engine import TemplateEngine
from engines.factory import create_template_engine
from processor.factory import create_content_processor
from processor.tailwind_processor import build_tailwind
from utils.fs_manager import FileSystemManager
from .plugin_manager import PluginManager
import json
import os
from pathlib import Path
import shutil
import subprocess
import yaml

from processor.factory import _PROCESSOR_MAP

import logging

supported_extensions = list(_PROCESSOR_MAP.keys())


# TODO: Complete hooks.
# TODO: Complete header navigation.


class Project:
    """
    Represents the entire website generation project.
    Manages global settings, source and output paths, and
    Orchestrates the build process.
    """

    def __init__(self, config: Config):
        """
        Initializes the project by loading configuration and setting up components.

        Args:
            config_path: Path to the YAML configuration file.
        """
        self.logger = logging.getLogger(__name__)

        self.config: Config = config
        # self.config.load(config_path)
        self.fs_manager: FileSystemManager = FileSystemManager()
        self.site: Site = Site(self.config)
        self.plugin_manager: PluginManager = PluginManager(self.config, self.site)
        self.plugin_manager.detect_and_load_plugins()
        self.plugin_manager.run_hook(
            "after_config_loaded",
            site=self.site,
            config=self.config,
            fs_manager=self.fs_manager,
        )
        self.template_engine: TemplateEngine = create_template_engine(
            self.config.settings["template_engine"],
            self.config.settings["template_dirs"],
        )

    def build(self) -> None:
        """Orchestrates the entire site generation process."""
        self.plugin_manager.run_hook(
            "before_build",
            site=self.site,
            config=self.config,
            fs_manager=self.fs_manager,
        )

        self.logger.info("Build process started.")

        self._discover_and_load_pages()
        self._load_site_data()
        self.plugin_manager.run_hook(
            "after_pages_discovered",
            site=self.site,
            config=self.config,
            fs_manager=self.fs_manager,
        )
        self._render_pages()
        self._export_json_data()
        self._build_react_section()
        self._build_tailwind()
        self._copy_assets()
        self.logger.info("Build process finished successfully.")

        self.plugin_manager.run_hook(
            "after_build",
            site=self.site,
            config=self.config,
            fs_manager=self.fs_manager,
        )

    def get_template_engine(self) -> TemplateEngine:
        """
        Returns the template engine instance used for rendering pages.

        Returns:
            TemplateEngine: The configured template engine.
        """
        return self.template_engine

    def _discover_and_load_pages(self) -> None:
        """Finds content files, creates Page objects, and loads their data."""
        self.logger.info("Discovering and loading site content...")

        output_dir = Path(self.config.get("output_directory"))
        collections = self.config.get("collections")
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
                    self.logger.warning(
                        f"Collection path does not exist: {collection_path}"
                    )
                    continue

                try:
                    page_filepaths = self.fs_manager.list_files(
                        collection_path, recursive=True
                    )
                except Exception as exc:
                    self.logger.error(
                        f"Failed to list files for collection '{name}': {exc}",
                        exc_info=True,
                    )
                    continue

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
                    self.plugin_manager.run_hook(
                        "before_page_parsed",
                        site=self.site,
                        config=self.config,
                        fs_manager=self.fs_manager,
                        page=page,
                    )
                    processor = create_content_processor(ext)
                    page.load(processor)

                    if not page.page_type:
                        collection_type = cfg.get("type")
                        if collection_type:
                            page.set_page_type(collection_type)

                    output_path = page.get_output_path()
                    if not output_path:
                        page.calculate_output_path(
                            output_dir, url_prefix=cfg.get("url_prefix")
                        )

                    page.generate_abs_url()
                    page.generate_root_rel_url()
                    self.site.add_page(page)
                    self.plugin_manager.run_hook(
                        "after_page_parsed",
                        site=self.site,
                        config=self.config,
                        fs_manager=self.fs_manager,
                        page=page,
                    )
        else:
            content_path = Path(self.config.get("source_directory"))
            page_filepaths = self.fs_manager.list_files(content_path, recursive=True)

            for path in page_filepaths:
                ext = os.path.splitext(path)[1].lstrip(".").lower()
                if ext in supported_extensions:
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

                    output_path = page.get_output_path()
                    if not output_path:
                        page.calculate_output_path(output_dir)

                    page.generate_abs_url()
                    page.generate_root_rel_url()
                    self.site.add_page(page)
                    self.plugin_manager.run_hook(
                        "after_page_parsed",
                        site=self.site,
                        config=self.config,
                        fs_manager=self.fs_manager,
                        page=page,
                    )

    def _render_pages(self) -> None:
        """Renders all loaded pages to their output files."""
        self.logger.info("Rendering pages...")
        header = self.site.populate_header()
        for page in self.site.pages:
            # self.plugin_manager.run_hook(
            #     "before_page_parsed",
            #     site=self.site,
            #     config=self.config,
            #     fs_manager=self.fs_manager,
            #     page=page,
            # )

            # 2. Build rendering context
            context = self._build_page_context(page, header)

            # self.plugin_manager.run_hook(
            #     "after_page_parsed",
            #     site=self.site,
            #     config=self.config,
            #     fs_manager=self.fs_manager,
            #     page=page,
            # )

            # 3. Template is determined by page metadata (with a fallback)
            # template_name = page.metadata.get("template", ["default.html"])[0]
            # TODO: Fix default template.
            template_name = self._resolve_template_name(page)

            self.plugin_manager.run_hook(
                "before_page_rendered",
                site=self.site,
                config=self.config,
                fs_manager=self.fs_manager,
                page=page,
            )

            rendered_html = self.template_engine.render(template_name, context)
            self.fs_manager.write_file(page.get_output_path(), rendered_html)
            self.logger.debug(
                f"Rendered page: {page.source_filepath} -> {page.get_output_path()}"
            )

            self.plugin_manager.run_hook(
                "after_page_rendered",
                site=self.site,
                config=self.config,
                fs_manager=self.fs_manager,
                page=page,
            )

    def _build_page_context(self, page: Page, header: str) -> dict:
        frontend = self.config.get("frontend", {})
        assets = frontend.get("assets", {}) if isinstance(frontend, dict) else {}

        stylesheets = list(assets.get("css") or [])
        scripts = list(assets.get("js") or [])

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

        context = page.get_context(
            header=header,
            site=self.site,
            stylesheets=stylesheets,
            scripts=scripts,
        )

        context_updates = self.plugin_manager.run_hook_collect(
            "modify_template_context",
            context=context,
            site=self.site,
            config=self.config,
            fs_manager=self.fs_manager,
            page=page,
        )
        for update in context_updates:
            if isinstance(update, dict):
                context.update(update)

        return context

    def _resolve_template_name(self, page: Page) -> str:
        template_value = page.metadata.get("template")
        template_name = None

        if template_value:
            if isinstance(template_value, list):
                template_name = template_value[0] if template_value else None
            else:
                template_name = template_value

        if not template_name and page.collection_config:
            template_name = page.collection_config.get("template")

        if not template_name:
            templates_by_type = self.config.get("templates_by_type", {})
            if isinstance(templates_by_type, dict):
                template_name = templates_by_type.get(page.page_type)

        return template_name or "post.html"

    def _build_tailwind(self) -> None:
        try:
            build_tailwind(self.config)
        except RuntimeError as exc:
            self.logger.error(str(exc), exc_info=True)
            raise

    def _build_react_section(self) -> None:
        react_cfg = self.config.get("react", {})
        if not isinstance(react_cfg, dict) or not react_cfg.get("enabled", False):
            return

        collection = react_cfg.get("collection")
        if not collection:
            self.logger.error("React build is enabled but no collection is set.")
            return

        app_dir = Path(react_cfg.get("app_dir", "./react-app"))
        if not app_dir.exists():
            self.logger.error(f"React app directory not found: {app_dir}")
            return

        export_subdir = react_cfg.get("export_subdir") or collection
        export_subdir = export_subdir.strip("/\\")
        base_path = react_cfg.get("base_path") or f"/{export_subdir}"
        if base_path and not str(base_path).startswith("/"):
            base_path = f"/{base_path}"
        asset_prefix = react_cfg.get("asset_prefix") or base_path
        if asset_prefix and not str(asset_prefix).startswith("/"):
            asset_prefix = f"/{asset_prefix}"

        frontend = self.config.get("frontend", {})
        export_data = (
            frontend.get("export_data", {}) if isinstance(frontend, dict) else {}
        )
        if not export_data.get("enabled", False):
            self.logger.error(
                "React build requires frontend.export_data.enabled = true."
            )
            return
        data_dir = Path(export_data.get("output_dir", "./output/data"))
        if not data_dir.exists():
            self.logger.error(
                f"React build requires JSON data at {data_dir}. "
                "Enable frontend.export_data and run build."
            )
            return

        public_data_dir = app_dir / "public" / "data"
        if public_data_dir.exists():
            shutil.rmtree(public_data_dir)
        self.fs_manager.copy_directory(data_dir, public_data_dir, exist_ok=True)

        env = os.environ.copy()
        env["NEXT_PUBLIC_BASE_PATH"] = base_path
        env["NEXT_PUBLIC_ASSET_PREFIX"] = asset_prefix
        env["NEXT_PUBLIC_COLLECTION"] = collection
        env["NEXT_PUBLIC_DATA_URL"] = "/data"

        try:
            npm = shutil.which("npm")
            if npm is None:
                raise RuntimeError("npm not found. Please install Node.js.")
            subprocess.run(
                [npm, "run", "build"],
                cwd=str(app_dir),
                env=env,
                check=True,
            )
        except FileNotFoundError as exc:
            self.logger.error("npm not found; React build skipped.", exc_info=True)
            raise RuntimeError("npm not found on PATH.") from exc
        except subprocess.CalledProcessError as exc:
            self.logger.error("React build failed.", exc_info=True)
            raise RuntimeError("React build failed.") from exc

        export_dir = app_dir / "out"
        if not export_dir.exists():
            self.logger.error(f"React export directory not found: {export_dir}")
            return

        output_dir = Path(self.config.get("output_directory"))
        dest_dir = output_dir / export_subdir
        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        self.fs_manager.copy_directory(export_dir, dest_dir, exist_ok=True)

    def _load_site_data(self) -> None:
        data_dir_value = self.config.get("data_dir")
        if not data_dir_value:
            return

        data_dir = Path(data_dir_value)
        if not data_dir.exists():
            self.logger.info(f"Data directory does not exist: {data_dir}")
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
                    f"Failed to load data file {data_file}: {exc}", exc_info=True
                )

        self.site.set_data(data)

    def _export_json_data(self) -> None:
        frontend = self.config.get("frontend", {})
        if not isinstance(frontend, dict):
            return

        export_data = frontend.get("export_data", {})
        if not isinstance(export_data, dict) or not export_data.get("enabled", False):
            return

        output_dir = Path(self.config.get("output_directory"))
        data_dir = Path(export_data.get("output_dir", "./output/data"))
        include_collections = export_data.get("include_collections")
        filter_collections = (
            isinstance(include_collections, list) and len(include_collections) > 0
        )

        site_payload: dict = {
            "site": {
                "name": self.config.get("site_name", ""),
                "description": self.config.get("site_description", ""),
                "base_url": self.config.get("base_url", ""),
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
        """
        Copies global site assets (e.g., CSS, JS, images) from source directories
        to the output directory.

        Always includes './styles' as default CSS template.
        Additional asset directories can be specified in config under 'asset_dirs'.
        """
        output_dir: Path = Path(self.config.get("output_directory"))

        # Get asset directories from config, always include './styles'
        asset_dirs = self.config.get("asset_dirs", [])
        if "./styles" not in asset_dirs:
            asset_dirs.insert(0, "./styles")

        for asset_dir in asset_dirs:
            asset_dir = Path(asset_dir)
            if os.path.exists(asset_dir):
                dest_dir = output_dir / asset_dir.name
                try:
                    self.fs_manager.copy_directory(asset_dir, dest_dir)
                    self.logger.info(
                        f"Copied asset directory: {asset_dir} -> {dest_dir}"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Failed to copy asset directory {asset_dir}: {e}",
                        exc_info=True,
                    )
            else:
                self.logger.warning(f"Asset directory does not exist: {asset_dir}")
