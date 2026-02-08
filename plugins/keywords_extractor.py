from core.site import Site
from .base_plugin import BasePlugin
from bs4 import BeautifulSoup


class PageKeyWordExtractor(BasePlugin):
    """
    Plugin that extracts keywords from each page's content and adds them to the page metadata.
    """

    def __init__(self) -> None:
        super().__init__()

    def after_page_parsed(self, **kwargs):
        # TODO: Maybe in future do weighted extraction.

        site: Site = kwargs.get("site")

        for p in site.get_pages():
            keywords = []
            html_tags_to_be_extracted = [
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
                "b",
                "strong",
                "i",
                "em",
            ]
            processed_content = p.processed_content

            # Simple keyword extraction based on html tags.
            soup = BeautifulSoup(processed_content, "html.parser")
            for tag in html_tags_to_be_extracted:
                for element in soup.find_all(tag):
                    text = element.get_text().strip()
                    if text and text not in keywords:
                        keywords.append(text)
            if not p.keywords or p.keywords == [] or p.keywords == "":
                p.keywords = keywords
