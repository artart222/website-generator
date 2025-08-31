from core.page import Page
from core.site import Site
from .base_plugin import BasePlugin
from typing import Optional


class BlogIndexerPlugin(BasePlugin):
    def on_config_loaded(self, config, site) -> None:
        return super().on_config_loaded(config, site)

    def on_before_build(self, site) -> None:
        return super().on_before_build(site)

    def on_after_build(self, site) -> None:
        blog_pages = [
            p
            for p in site.get_pages()
            if p.get_page_type() is not None and "blog" in p.get_page_type()
        ]

        # Build simple HTML list
        items = "\n".join(
            f"<li><article><a href='{p.get_output_path()}'>{p.title}</a></article></li>"
            for p in blog_pages
        )

        # Create a new Page object
        index_page = Page(source_filepath="", config=None, fs_manager=None)
        index_page.add_metadata({"template": "blog-indexer.html"})
        index_page.set_output_path("./output/blog-indexer/blog-indexer.html")
        index_page.set_processed_content(items)

        # Add to site pages
        site.add_page(index_page)
        site.logger.info("Blog index page generated.")

    def on_page_parsed(self, page: Page, site: Site) -> None:
        pass

    def on_page_rendered(self, page: Optional[Page], site: Site) -> None:
        return super().on_page_rendered(page, site)
