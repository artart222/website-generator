from pathlib import Path

from datetime import date

from xml.sax.saxutils import escape

from core.config import Config
from core.site import Site
from .base_plugin import BasePlugin


class SitemapPlugin(BasePlugin):
    """
    Generates sitemap.xml for the site.
    Should be attached to the plugin system.
    """

    def __init__(self, special_types=None):
        super().__init__()

    def after_build(self, **kwargs):
        """
        Called after the site build is complete.
        Generates sitemap.xml for all pages.
        """
        site: Site = kwargs["site"]
        config: Config = kwargs["config"]

        output_dir = Path(config.get("output_directory"))

        sitemap_entries = []

        for page in site.get_pages():
            self.logger.debug(
                f"Processing page for sitemap: {page.title} ({page.get_root_rel_url()})"
            )
            url = page.get_root_rel_url()

            # last modified date (Today)
            lastmod = getattr(page, "last_modified", date.today()).isoformat()
            if page.get_root_rel_url() == "/":
                priority = "1.0"
            else:
                priority = "0.8"

            # Escape URL for XML safety
            url_escaped = escape(url)

            sitemap_entries.append(f"""
  <url>
    <loc>{url_escaped}</loc>
    <lastmod>{lastmod}</lastmod>
    <priority>{priority}</priority>
  </url>""")

        sitemap_content = "<?xml version='1.0' encoding='UTF-8'?>\n"
        sitemap_content += (
            '<urlset xmlns="https://www.sitemaps.org/schemas/sitemap/0.9">\n'
        )
        sitemap_content += "\n".join(sitemap_entries)
        sitemap_content += "\n</urlset>"

        # Write sitemap.xml
        sitemap_file = output_dir / "sitemap.xml"
        sitemap_file.write_text(sitemap_content, encoding="utf-8")
