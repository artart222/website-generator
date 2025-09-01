import logging
from .base_plugin import BasePlugin
from core.config import Config
from core.site import Site
from core.page import Page
from utils.fs_manager import FileSystemManager


class SpecialPagesPlugin(BasePlugin):
    """
    Adjusts output paths and URLs for special pages like 'home' or 'blog-index'.
    Should run after all pages are loaded but before rendering.
    """

    def __init__(self, special_types=None):
        """
        Args:
            special_types: List of page types that should be treated specially.
                           Defaults to ['home', 'blog-index'].
        """
        self.logger = logging.getLogger(__name__)
        self.special_types = special_types or ["index", "blog-index"]

    def on_before_page_rendered(self, **kwargs):
        """
        Modify output paths and URLs for pages of special types.
        """
        site = kwargs.get("site")
        config = kwargs.get("config")
        fs_manager = kwargs.get("fs_manager")

        self.logger.debug("SpecialPagesPlugin started working")

        if not isinstance(site, Site):
            msg = (
                "Missing or invalid 'site' argument in BlogIndexerPlugin.on_after_build"
            )
            self.logger.warning(msg)
            raise ValueError(msg)

        if not isinstance(config, Config):
            msg = "Missing or invalid 'config' argument in BlogIndexerPlugin.on_after_build"
            self.logger.warning(msg)
            raise ValueError(msg)

        if not isinstance(fs_manager, FileSystemManager):
            msg = "Missing or invalid 'fs_manager' argument in BlogIndexerPlugin.on_after_build"
            self.logger.warning(msg)
            raise ValueError(msg)

        for page in site.pages:
            page_types = page.get_page_type()
            if not page_types:
                continue

            # Check if page has a special type
            for ptype in page_types:
                if ptype in self.special_types:
                    # Determine output path
                    output_dir = site.config.get("output_directory")
                    if ptype == "index" or ptype == "home":
                        page.set_output_path(output_dir + "/" + "index.html")
                    elif ptype == "blog-index":
                        page.set_output_path(
                            output_dir + "/" + "blog-index" + "/" + "index.html"
                        )
                    else:
                        # Default handling if more types added later
                        page.set_output_path(
                            output_dir
                            + "/"
                            + ptype
                            + "/"
                            + page.get_slug()
                            + "/"
                            + "index.html"
                        )

                    # Re-generate URL
                    if ptype == "index":
                        self.generate_special_url(page)
                    else:
                        page.generate_url()
                    self.logger.info(
                        f"Special page handled: {page.title} -> {page.get_output_path()} -> {page.get_url()}"
                    )

    def on_after_build(self, **kwargs):
        """No action needed for page builded."""
        pass

    def on_before_build(self, **kwargs):
        """Nothing to do before build."""
        pass

    def on_config_loaded(self, **kwargs):
        """Nothing to do during config loading."""
        pass

    def on_page_parsed(self, **kwargs):
        """No action needed for page parsed."""
        pass

    def on_page_rendered(self, **kwargs):
        """No action needed for page rendered."""
        pass

    def generate_special_url(self, page: Page) -> str:
        """
        Generates URL for special cases (home/index page).

        Args:
            page: The Page object.

        Returns:
            str: The URL if it's a special case, otherwise None.
        """
        base_url = page.config.get("base_url", "") if page.config else ""

        if page.page_type in ("home", "index") or page.slug == "index":
            page.url = "/" if not base_url else base_url.rstrip("/") + "/"
            return page.url

        return ""
