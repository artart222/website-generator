from abc import ABC, abstractmethod
from typing import Optional
from core.page import Page
from core.config import Config
from core.site import Site


class BasePlugin(ABC):
    """Base class for all plugins."""

    @abstractmethod
    def on_config_loaded(self, config: Config, site: Site) -> None:
        """
        Called after the configuration file is loaded.
        """

    @abstractmethod
    def on_before_build(self, site: Site) -> None:
        """
        Called before the site build starts.
        """

    @abstractmethod
    def on_page_parsed(self, page: Page, site: Site) -> None:
        """
        Called after a Page object is created and parsed.
        """

    @abstractmethod
    def on_page_rendered(self, page: Optional[Page], site: Site) -> None:
        """
        Called after a Page is rendered into HTML.
        """

    @abstractmethod
    def on_after_build(self, site: Site) -> None:
        """
        Called after the whole site is built.
        """
