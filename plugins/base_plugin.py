from abc import ABC, abstractmethod
from typing import Any


class BasePlugin(ABC):
    """Base class for all plugins."""

    @abstractmethod
    def on_config_loaded(self, *args, **kwargs) -> Any:
        """
        Called after the configuration file is loaded.
        """

    @abstractmethod
    def on_before_build(self, *args, **kwargs) -> Any:
        """
        Called before the site build starts.
        """

    @abstractmethod
    def on_page_parsed(self, *args, **kwargs) -> Any:
        """
        Called after a Page object is created and parsed.
        """

    @abstractmethod
    def on_page_rendered(self, *args, **kwargs) -> Any:
        """
        Called after a Page is rendered into HTML.
        """

    @abstractmethod
    def on_after_build(self, *args, **kwargs) -> Any:
        """
        Called after the whole site is built.
        """
