from pathlib import Path
from core.site import Site
from .base_plugin import BasePlugin


class SpecialPagesPlugin(BasePlugin):
    """
    Adjusts output paths and URLs for special pages like 'home' or 'blog-indexer'.
    Should run after all pages are loaded but before rendering.
    """

    def __init__(self, special_types=None):
        """
        Args:
            special_types: List of page types that should be treated specially.
                           Defaults to ['index', 'blog-indexer'].
        """
        super().__init__()
        self.special_types = special_types or ["index", "blog-indexer"]

    def before_page_parsed(self, **kwargs):
        """
        Modify output paths and URLs for pages of special types.
        """
        site: Site = kwargs["site"]
        output_dir = Path(site.config.get("output_directory", "output"))
        base_url = site.config.get("base_url", "").rstrip("/")

        for page in site.pages:
            page_types = page.get_page_type()
            if not page_types:
                continue

            # Check if page has a special type
            for ptype in page_types:
                if ptype not in self.special_types:
                    continue

                # Handle home/index page
                if ptype in ["index", "home"]:
                    page.set_output_path(str(output_dir / "index.html"))
                    page.set_rel_url("/")
                    page.abs_url = f"{base_url}/" if base_url else "/"

                # Handle blog index page
                elif ptype == "blog-indexer":
                    page.set_output_path(str(output_dir / "blog-indexer" / "index.html"))
                    page.set_rel_url("/blog-indexer/")
                    page.abs_url = (
                        f"{base_url}/blog-indexer/" if base_url else "/blog-indexer/"
                    )

                # Future special types can be added here
                else:
                    # Default behavior: use page_type + slug
                    page.set_output_path(
                        str(output_dir / ptype / page.get_slug() / "index.html")
                    )
                    page.generate_abs_url()
                    page.generate_root_rel_url()

                self.logger.info(
                    f"Special page handled: {page.title} -> "
                    f"{page.get_output_path()} -> {page.get_abs_url()}"
                )
