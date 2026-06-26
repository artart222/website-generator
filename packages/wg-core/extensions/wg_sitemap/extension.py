from wg_contracts.extension import BaseExtension


class SitemapExtension(BaseExtension):
    name = "wg-sitemap"


def get_extension() -> SitemapExtension:
    return SitemapExtension()
