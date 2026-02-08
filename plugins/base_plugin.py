from typing import Any
from abc import ABC
import logging
from core.config import Config
from core.site import Site
from utils.fs_manager import FileSystemManager
from functools import wraps


class BasePlugin(ABC):
    """Base class for all plugins."""

    def __init__(self):
        self.logger = logging.getLogger(f"plugin.{self.__class__.__name__}")

    def validate_args(self, hook_name: str, **kwargs):
        """
        Automatically check common kwargs and log errors.
        """
        if "site" in kwargs and not isinstance(kwargs["site"], Site):
            msg = f"Invalid 'site' argument in {self.__class__.__name__}.{hook_name}"
            self.logger.warning(msg)
            raise ValueError(msg)

        if "config" in kwargs and not isinstance(kwargs["config"], Config):
            msg = f"Invalid 'config' argument in {self.__class__.__name__}.{hook_name}"
            self.logger.warning(msg)
            raise ValueError(msg)

        if "fs_manager" in kwargs and not isinstance(
            kwargs["fs_manager"], FileSystemManager
        ):
            msg = f"Invalid 'fs_manager' argument in {self.__class__.__name__}.{hook_name}"
            self.logger.warning(msg)
            raise ValueError(msg)

    @staticmethod
    def log_hook(func):
        """
        Decorator to automatically log entry/exit and validate common args.
        """

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            hook_name = func.__name__
            self.logger.debug(f"{self.__class__.__name__}: {hook_name} hook entered")

            # Validate common arguments
            self.validate_args(hook_name, **kwargs)

            result = func(self, *args, **kwargs)
            self.logger.debug(f"{self.__class__.__name__}: {hook_name} hook finished")
            return result

        return wrapper

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for attr, val in cls.__dict__.items():
            if (
                callable(val)
                and not attr.startswith("_")
                and attr
                in [
                    "after_config_loaded",
                    "before_build",
                    "after_pages_discovered",
                    "before_page_rendered",
                    "after_page_parsed",
                    "after_page_rendered",
                    "after_build",
                ]
            ):
                setattr(cls, attr, cls.log_hook(val))

    @log_hook
    def after_config_loaded(self, *args, **kwargs) -> Any:
        """
        Called after the configuration file is loaded.
        """
        pass

    @log_hook
    def before_build(self, *args, **kwargs) -> Any:
        """
        Called before the site build starts.
        """
        pass

    @log_hook
    def before_page_parsed(self, *args, **kwargs) -> Any:
        """
        Called before a Page object is created and parsed.
        """
        pass

    @log_hook
    def after_page_parsed(self, *args, **kwargs) -> Any:
        """
        Called after a Page object is created and parsed.
        """
        pass

    @log_hook
    def after_page_rendered(self, *args, **kwargs) -> Any:
        """
        Called after a Page is rendered into HTML.
        """
        pass

    @log_hook
    def before_page_rendered(self, *args, **kwargs) -> Any:
        """
        Called before a Page is rendered into HTML.
        """
        pass

    @log_hook
    def after_build(self, *args, **kwargs) -> Any:
        """
        Called after the whole site is built.
        """
        pass

    @log_hook
    def after_pages_discovered(self, *args, **kwargs) -> Any:
        """Called after all pages are loaded but before rendering."""
        pass
