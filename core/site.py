import logging
from .config import Config
from .page import Page
from typing import Iterator


class Site:
    """
    Represents the website to be generated as a data model.
    Contains all pages and site-wide metadata.
    """

    def __init__(self, config: Config) -> None:
        self.logger = logging.getLogger(__name__)
        self.config: Config = config

        self.name: str = config.get("site_name", "Default Site Name")
        self.base_url: str = config.get("base_url", "/")
        self.pages: list[Page] = []

        self.logger.debug(f"Site object created for '{self.name}'.")

    def add_page(self, page: Page) -> None:
        """
        Adds a fully loaded Page object to the site's collection.

        Args:
            page: A single Page object to add.
        """
        self.pages.append(page)
        self.logger.debug(f"Page '{page.source_filepath}' added to site.")

    def get_pages(self) -> list[Page]:
        """
        Returns a list of website pages.

        Returns:
            List of website pages.
        """
        return self.pages

    def get_page_by_url(self, url: str) -> Page | None:
        """
        Retrieve a page by its URL.

        Args:
            url: The URL of the page to find.

        Returns:
            The matching Page instance if found, otherwise None.
        """
        for page in self.pages:
            if page.url == url:
                return page
        return None

    # It seems this make page iterable.
    def __iter__(self) -> Iterator[Page]:
        return iter(self.pages)

    # The repr() function makes string representation of an object.
    def __repr__(self) -> str:
        return f"<Site name='{self.name}' pages={len(self.pages)}>"

    def __len__(self) -> int:
        return len(self.pages)
