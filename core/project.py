from .site import Site
from .config import Config
from .page import Page
from engines.base_engine import TemplateEngine
from engines.factory import create_template_engine
from processor.factory import create_content_processor
from utils.fs_manager import FileSystemManager
from plugins.blog_indexer import BlogIndexerPlugin
from .plugin_manager import PluginManager
import os

import logging


class Project:
    """
    Represents the entire website generation project.
    Manages global settings, source and output paths, and
    Orchestrates the build process.
    """

    def __init__(self, config_path: str):
        """Initializes the project by loading configuration."""
        self.logger = logging.getLogger(__name__)

        self.config = Config()
        self.config.load(config_path)
        self.site = Site(self.config)
        self.plugin_manager = PluginManager(self.config, self.site)
        self.fs_manager = FileSystemManager()
        self.template_engine = create_template_engine(
            self.config.settings["template_engine"],
            self.config.settings["template_dirs"],
        )

    def build(self) -> None:
        """Orchestrates the entire site generation process."""
        self.logger.info("Build process started.")
        self.plugin_manager.detect_and_load_plugins()

        self._discover_and_load_pages()
        self.fs_manager.copy_directory(
            "./styles", f"{self.config.get('output_directory')}/styles"
        )
        # self._copy_assets() # TODO: Make this
        # blog_indexer_plugin = BlogIndexerPlugin()
        # blog_indexer_plugin.on_after_build(self.site)
        self.plugin_manager.run_hook("on_after_build", self.site)
        self._render_pages()

        self.logger.info("Build process finished successfully.")

    def get_template_engine(self) -> TemplateEngine:
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
                page.load(self.fs_manager, processor)

                if page.get_output_path() == "":
                    output_path = page.calculate_output_path(output_dir)
                else:
                    output_path = page.get_output_path()
                page.set_output_path(output_path)
                self.site.add_page(page)

    def _render_pages(self) -> None:
        """Renders all loaded pages to their output files."""
        self.logger.info("Rendering pages...")

        for page in self.site.pages:
            # 2. Page provides its own rendering context
            context = page.get_context()

            # 3. Template is determined by page metadata (with a fallback)
            # template_name = page.metadata.get("template", ["default.html"])[0]
            template_name = page.metadata.get("template", "post.html")

            rendered_html = self.template_engine.render(template_name, context)
            self.fs_manager.write_file(page.get_output_path(), rendered_html)
            self.logger.debug(
                f"Rendered page: {page.source_filepath} -> {page.get_output_path()}"
            )
