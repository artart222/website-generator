from core.site import Site
from .base_plugin import BasePlugin
from core.page import Page


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
        super().__init__()
        self.special_types = special_types or ["index", "blog-index"]

    def before_page_rendered(self, **kwargs):
        """
        Modify output paths and URLs for pages of special types.
        """
        site: Site = kwargs["site"]

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
                        # TODO: Fix this
                        page.set_output_path(output_dir + "/" + "index.html")
                        page.set_rel_url("/")
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
                        page.generate_abs_url()
                    self.logger.info(
                        f"Special page handled: {page.title} -> {page.get_output_path()} -> {page.get_abs_url()}"
                    )

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
            page.abs_url = "/" if not base_url else base_url.rstrip("/") + "/"
            return page.abs_url

        return ""
