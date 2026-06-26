"""Plugin base class and lifecycle event vocabulary.

Plugins subclass :class:`BasePlugin` and override the lifecycle hooks they care
about. Hooks are plain methods - there is no metaclass or ``__init_subclass__``
magic rewriting them, so behavior is explicit and debuggable. Error handling is
owned by :class:`core.plugin_manager.PluginManager` (strict vs lenient), not by
each plugin.
"""

from __future__ import annotations

import logging
from abc import ABC
from enum import Enum
from typing import Any


class LifecycleEvent(str, Enum):
    """Named build lifecycle events a plugin can hook into.

    Using an enum documents the available extension points in one place and
    lets callers reference ``LifecycleEvent.AFTER_BUILD.value`` instead of bare
    strings. ``PluginManager`` dispatches by the string value.
    """

    AFTER_CONFIG_LOADED = "after_config_loaded"
    BEFORE_BUILD = "before_build"
    AFTER_COLLECTIONS_LOADED = "after_collections_loaded"
    AFTER_PAGES_DISCOVERED = "after_pages_discovered"
    BEFORE_PAGE_PARSED = "before_page_parsed"
    AFTER_DOCUMENT_LOADED = "after_document_loaded"
    AFTER_PAGE_PARSED = "after_page_parsed"
    AFTER_ROUTES_BUILT = "after_routes_built"
    BEFORE_PAGE_RENDERED = "before_page_rendered"
    AFTER_PAGE_RENDERED = "after_page_rendered"
    AFTER_BUILD = "after_build"
    MODIFY_CONTEXT = "modify_context"
    MODIFY_TEMPLATE_CONTEXT = "modify_template_context"
    INJECT_CSS = "inject_css"
    INJECT_JS = "inject_js"


class BasePlugin(ABC):
    """Base class for all plugins.

    Override any subset of the lifecycle hooks below. Hooks receive keyword
    arguments describing the current build state (commonly ``site``, ``config``,
    ``fs_manager`` and ``page``). Returning a value is only meaningful for the
    "collect" hooks (``inject_css``, ``inject_js``, ``modify_context``,
    ``modify_template_context``).
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"plugin.{self.__class__.__name__}")

    def after_config_loaded(self, **kwargs: Any) -> Any:
        """Called after configuration is loaded and managers are created."""

    def before_build(self, **kwargs: Any) -> Any:
        """Called before the site build starts."""

    def after_collections_loaded(self, **kwargs: Any) -> Any:
        """Called after collections/documents are discovered."""

    def before_page_parsed(self, **kwargs: Any) -> Any:
        """Called before a Page object is created and parsed."""

    def after_page_parsed(self, **kwargs: Any) -> Any:
        """Called after a Page object is created and parsed."""

    def after_document_loaded(self, **kwargs: Any) -> Any:
        """Called after a source document is parsed."""

    def after_routes_built(self, **kwargs: Any) -> Any:
        """Called after output paths and public URLs are assigned."""

    def before_page_rendered(self, **kwargs: Any) -> Any:
        """Called before a Page is rendered into HTML."""

    def after_page_rendered(self, **kwargs: Any) -> Any:
        """Called after a Page is rendered into HTML."""

    def after_build(self, **kwargs: Any) -> Any:
        """Called after the whole site is built."""

    def after_pages_discovered(self, **kwargs: Any) -> Any:
        """Called after all pages are loaded but before rendering."""

    def modify_template_context(self, **kwargs: Any) -> Any:
        """Return a dict to merge into a page's template context."""

    def modify_context(self, **kwargs: Any) -> Any:
        """Alias for :meth:`modify_template_context`."""

    def inject_css(self, **kwargs: Any) -> Any:
        """Return stylesheet href(s) to inject into a page."""

    def inject_js(self, **kwargs: Any) -> Any:
        """Return script src(s) to inject into a page."""
