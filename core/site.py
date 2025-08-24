import logging
from .config import Config
from .page import Page


class Site:
    """
    Represents the website to be generated as a data model.
    Contains all pages and site-wide metadata.
    """

    def __init__(self, config: Config) -> None:
        self.logger = logging.getLogger(__name__)
        self.config = config

        self.name: str = config.get("site_name", "Default Site Name")
        self.base_url: str = config.get("base_url", "/")
        self.pages: list[Page] = []

        self.logger.debug(f"Site object created for '{self.name}'.")

    def add_page(self, page: Page) -> None:
        """
        Adds a fully loaded Page object to the site's collection.

        Args:
            page: List of website pages.
        """
        self.pages.append(page)
        self.logger.debug(f"Page '{page.source_filepath}' added to site.")
