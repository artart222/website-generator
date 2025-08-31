from core.page import Page
from core.site import Site
from .base_plugin import BasePlugin
import logging


class BlogIndexerPlugin(BasePlugin):
    """
    Plugin that generates a blog index page listing all pages
    whose type contains 'blog'. Adds the index page to the site after build.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def on_config_loaded(self, **kwargs):
        """Nothing to do during config loading."""
        pass

    def on_before_build(self, **kwargs):
        """Nothing to do before build."""
        pass

    def on_after_build(self, **kwargs) -> None:
        """
         Generate the blog index page after all pages are built.

        Expected kwargs:
            site (Site): The Site object
        """
        site = kwargs.get("site")
        msg = "Missing or invalid 'site' argument in BlogIndexerPlugin.on_after_build"
        self.logger.warning(msg)
        if not isinstance(site, Site):
            raise ValueError(msg)

        blog_pages = [
            p
            for p in site.get_pages()
            if p.get_page_type() is not None and "blog" in p.get_page_type()
        ]

        self.logger.debug(f"Detected blog pages: {blog_pages}")

        # Build simple HTML list
        list_items = "\n".join(
            f"<li><article><a href='{'../' + '/'.join(p.get_output_path().split('/')[1:])}'>{p.title}</a></article></li>"
            for p in blog_pages
        )
        html_list = f"<ul>{list_items}</ul>"

        # Create a new Page object
        self.logger.debug("Generating virtual index page")
        index_page = Page(source_filepath="", config=None, fs_manager=None)
        index_page.add_metadata({"template": "blog-indexer.html"})
        index_page.set_output_path("./output/blog-indexer/blog-indexer.html")
        index_page.set_processed_content(html_list)

        # Add to site pages
        site.add_page(index_page)
        site.logger.debug("Blog index page generated.")

    def on_page_parsed(self, **kwargs):
        """No action needed for page parsed."""
        pass

    def on_page_rendered(self, **kwargs):
        """No action needed for page rendered."""
        pass
