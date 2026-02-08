from core.page import Page
from core.site import Site
from core.config import Config
from utils.fs_manager import FileSystemManager
from .base_plugin import BasePlugin


class BlogIndexerPlugin(BasePlugin):
    """
    Plugin that generates a blog index page listing all pages
    whose type contains 'blog'. Adds the index page to the site after build.
    """

    def __init__(self) -> None:
        super().__init__()

    def after_pages_discovered(self, **kwargs) -> None:
        """
         Generate the blog index page after all pages are built.

        Expected kwargs:
            site (Site): The Site object
            config (Config): The site config object
            fs_manager (FileSystemManager): The site file system manager.
        """
        site: Site = kwargs.get("site")
        config: Config = kwargs.get("config")
        fs_manager: FileSystemManager = kwargs.get("fs_manager")

        blog_pages = [
            p
            for p in site.get_pages()
            if p.get_page_type() is not None and "blog" in p.get_page_type()
        ]

        self.logger.debug(f"Detected blog pages: {blog_pages}")

        # Build simple HTML list
        list_items = "\n".join(
            f"<li><article><a href='{p.get_root_rel_url()}'>{p.title}</a></article></li>"
            for p in blog_pages
        )
        html_list = f"<ul>{list_items}</ul>"

        # Create a new Page object
        self.logger.debug("Generating virtual index page")
        index_page = Page(source_filepath="", config=config, fs_manager=fs_manager)
        index_page.add_metadata({"template": "blog-indexer.html"})
        index_page.calculate_output_path(
            config.get("output_directory") + "/blog-indexer"
        )
        index_page.set_page_type("blog-indexer")
        index_page.set_processed_content(html_list)
        index_page.generate_abs_url()
        index_page.generate_root_rel_url()

        # Add to site pages
        site.add_page(index_page)
