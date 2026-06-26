from wg_contracts.extension import BaseExtension


class SeoExtension(BaseExtension):
    name = "wg-seo"


def get_extension() -> SeoExtension:
    return SeoExtension()
