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
        self.header = ""

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
            if page.abs_url == url:
                return page
        return None

    def get_page_by_type(self, type: str) -> list[Page]:
        """
        Returns a a list of pages with given type.

        Args:
            type: The type of the pages to find.

        Returns:
            The matching Page instances if found.
        """
        pages = []
        for page in self.pages:
            page_types = page.get_page_type()
            if page_types and type in page_types:
                pages.append(page)
        return pages

    def populate_header(self) -> str:
        header_config: list[dict] = self.config.get("navigation", "")
        header_str = ""
        for header_item in header_config:
            for page in self.get_pages():
                if header_item.get("type") in page.get_page_type():
                    header_str = (
                        header_str
                        + "\n"
                        + f"<li><a href='{page.get_root_rel_url()}'>{header_item.get('title')}</a></li>"
                    )
        self.header = header_str
        return header_str

    # It seems this make page iterable.
    def __iter__(self) -> Iterator[Page]:
        return iter(self.pages)

    # The repr() function makes string representation of an object.
    def __repr__(self) -> str:
        return f"<Site name='{self.name}' pages={len(self.pages)}>"

    def __len__(self) -> int:
        return len(self.pages)
