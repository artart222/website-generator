from extensions.base import BaseExtension


class SitemapExtension(BaseExtension):
    name = "wg-sitemap"


def get_extension() -> SitemapExtension:
    return SitemapExtension()
