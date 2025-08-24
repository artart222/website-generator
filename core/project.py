from .site import Site
from .config import Config
from .page import Page
from engines.base_engine import TemplateEngine
from engines.factory import create_template_engine
from processor.factory import create_content_processor
from utils.fs_manager import FileSystemManager
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
        # self.plugin_manager
        self.fs_manager = FileSystemManager()
        self.template_engine_instance = create_template_engine(
            self.config.settings["template_engine"],
            self.config.settings["template_dirs"],
        )

    def build(self):
        """Orchestrates the entire site generation process."""
        self.logger.info("Starting build...")
        self._discover_and_load_pages()
        for page in self.site.pages:
            page.read_source_file()
            contex_data = {
                "page_title": page.get_title(),
                "content": page.get_contex(),
            }
            # TODO: Change this in future and add auto template detection.
            rendered_html = self.template_engine_instance.render(
                "post.html", contex_data
            )

            # Splits the file name by dot and
            # excludes the last item which is extension
            # Make a list with that
            # Join the items of list with dot
            print(page.get_source_filepath())
            print(page.get_source_filepath().split(".")[:-1])
            output_file_name = ".".join(
                page.get_source_filepath().split(".")[:-1]
            ).split("\\")[-1]
            print(f"Output file name ==> '{output_file_name}.html'")
            self.fs_manager.write_file(f"output/{output_file_name}.html", rendered_html)
        self.fs_manager.copy_directory("styles", "output/styles")

        # self.site.discover_assets()
        # Add rendering logic here later.
        print("Build finished.")

    def get_template_engine(self) -> TemplateEngine:
        return self.template_engine_instance

    def _discover_and_load_pages(self):
        """Finds content files, creates Page objects, and loads their data."""
        self.logger.info("Discovering and loading site content...")

        content_path = self.config.get("source_directory")
        page_filepaths = self.fs_manager.list_files(content_path, recursive=True)

        for path in page_filepaths:
            if os.path.splitext(path)[1].lstrip(".") == "md":
                page = Page(path, self.config, self.fs_manager)
                # 2. Get the correct content processor from factory
                extension = os.path.splitext(path)[1].lstrip(".")
                processor = create_content_processor(extension)
                page.load(self.fs_manager, processor)
                self.site.add_page(page)
