from .site import Site
from .config import Config
from .page import Page
from engines.base_engine import TemplateEngine
from engines.factory import create_template_engine
from processor.factory import create_content_processor
from utils.fs_manager import FileSystemManager
from .plugin_manager import PluginManager
import os

import logging

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
        self.site: Site = Site(self.config)
        self.plugin_manager: PluginManager = PluginManager(self.config, self.site)
        self.fs_manager: FileSystemManager = FileSystemManager()
        self.template_engine: TemplateEngine = create_template_engine(
            self.config.settings["template_engine"],
            self.config.settings["template_dirs"],
        )

    def build(self) -> None:
        """Orchestrates the entire site generation process."""
        self.logger.info("Build process started.")
        self.plugin_manager.detect_and_load_plugins()
        self._discover_and_load_pages()
        self.plugin_manager.run_hook(
            "after_pages_discovered",
            site=self.site,
            config=self.config,
            fs_manager=self.fs_manager,
        )
        self._render_pages()
        self._copy_assets()
        self.plugin_manager.run_hook(
            "after_build",
            site=self.site,
            config=self.config,
            fs_manager=self.fs_manager,
        )
        self.logger.info("Build process finished successfully.")

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

        content_path = self.config.get("source_directory")
        page_filepaths = self.fs_manager.list_files(content_path, recursive=True)

        output_dir = self.config.get("output_directory")

        for path in page_filepaths:
            if os.path.splitext(path)[1].lstrip(".") == "md":
                page = Page(path, self.config, self.fs_manager)
                # 2. Get the correct content processor from factory
                extension = os.path.splitext(path)[1].lstrip(".")
                processor = create_content_processor(extension)
                page.load(processor)

                if page.get_output_path() == "":
                    output_path = page.calculate_output_path(output_dir)
                else:
                    output_path = page.get_output_path()
                page.set_output_path(output_path)
                page.generate_abs_url()
                page.generate_root_rel_url()
                self.site.add_page(page)

    def _render_pages(self) -> None:
        """Renders all loaded pages to their output files."""
        self.logger.info("Rendering pages...")
        for page in self.site.pages:
            # 2. Page provides its own rendering context
            context = page.get_context(self.site.populate_header())

            self.plugin_manager.run_hook(
                "after_page_parsed",
                site=self.site,
                config=self.config,
                fs_manager=self.fs_manager,
                page=page,
            )

            # 3. Template is determined by page metadata (with a fallback)
            # template_name = page.metadata.get("template", ["default.html"])[0]
            # TODO: Fix default template.
            template_name = page.metadata.get("template", "post.html")

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

    def _copy_assets(self) -> None:
        """
        Copies global site assets (e.g., CSS, JS, images) from source directories
        to the output directory.

        Always includes './styles' as default CSS template.
        Additional asset directories can be specified in config under 'asset_dirs'.
        """
        output_dir: str = self.config.get("output_directory")

        # Get asset directories from config, always include './styles'
        asset_dirs = self.config.get("asset_dirs", [])
        if "./styles" not in asset_dirs:
            asset_dirs.insert(0, "./styles")

        for asset_dir in asset_dirs:
            if os.path.exists(asset_dir):
                dest_dir = os.path.join(output_dir, os.path.basename(asset_dir))
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
