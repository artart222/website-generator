from .site import Site
from .config import Config

# from .page import Page
from engines.base_engine import TemplateEngine
from engines.factory import create_template_engine
from processor.base_processor import ContentProcessor
from processor.factory import create_content_processor
from utils.fs_manager import FileSystemManager

"""
Project

Attributes:

config: Configuration - Holds all project settings.

site: Site - The main site object to be built.

plugin_manager: PluginManager - Manages active plugins.

fs_manager: FileSystemManager - Utility for file operations.

template_engine_instance: TemplateEngine - The chosen template engine.

Methods:

__init__(config_path: str): Initializes the project by loading configuration.

load_plugins(): Discovers and loads configured plugins.

initialize_site(): Creates and populates the Site object based on source files and config.

build(): Orchestrates the entire site generation process (e.g., pre-build hooks, page rendering, asset copying, post-build hooks).

get_template_engine() -> TemplateEngine: Returns the configured template engine.
"""


class Project:
    """
    Represents the entire website generation project.
    Manages global settings, source and output paths, and
    Orchestrates the build process.
    """

    def __init__(self, config_path: str):
        """Initializes the project by loading configuration."""
        self.config = Config()
        self.config.load(config_path)
        self.site = Site(self.config)
        # self.plugin_manager
        self.fs_handler = FileSystemManager()
        self.template_engine_instance = create_template_engine(
            self.config.settings["template_engine"]
        )

    def build(self):
        """Orchestrates the entire site generation process."""
        print("Starting build...")
        # fs_handler = FileSystemManager()
        # md_processor = MarkdownProcessor(["extra", "meta", "codehilite"])
        # test_page = Page("")
        # test_page.read_source_file("source/main.md")
        # test_page.process_content(md_processor)
        # test_page.process_metadata(md_processor)
        # test_page.set_page_type()
        # print(test_page.get_page_type())

        # template_engine = DjangoTemplateEngine()
        # context_data = {"page_title": test_page.get_title(), "content": test_page.get_contex()}
        # rendered_html = template_engine.render("post", context_data)

        # fs_handler.write_file("output/output.html", rendered_html)
        # fs_handler.copy_directory("styles", "output/styles")
        site_pages = self.site.discover_content(
            self.config.get("source_directory"), self.config.get("pages_dir")
        )
        for page in site_pages:
            page.read_source_file()
            file_extension = page.get_source_filepath().split(".")[-1]
            content_processor = create_content_processor(file_extension)
            page.process_content(content_processor)
            page.process_metadata(content_processor)
            page.set_page_type()
            context_data = {
                "page_title": page.get_title(),
                "content": page.get_contex(),
            }
            rendered_html = self.template_engine_instance.render("post", context_data)

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
            self.fs_handler.write_file(f"output/{output_file_name}.html", rendered_html)
        self.fs_handler.copy_directory("styles", "output/styles")

        # self.site.discover_assets()
        # Add rendering logic here later.
        print("Build finished.")

    def get_template_engine(self) -> TemplateEngine:
        return self.template_engine_instance
