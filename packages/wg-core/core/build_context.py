"""Shared state passed between build steps.

A single ``BuildContext`` object carries the collaborators and mutable build
state so that each :class:`~core.build_pipeline.BuildStep` is decoupled from the
``Project`` facade and can be unit-tested in isolation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from wg_contracts.ports import FileSystemPort, TemplateEnginePort
from .config import Config
from .extension_manager import ExtensionManager
from .frontend_manager import FrontendManager
from .plugin_manager import PluginManager
from .router import Router
from .runtime_manager import RuntimeManager
from .site import Site
from .theme_manager import ThemeManager


@dataclass
class BuildContext:
    config: Config
    fs_manager: FileSystemPort
    site: Site
    router: Router
    theme_manager: ThemeManager
    plugin_manager: PluginManager
    extension_manager: ExtensionManager
    frontend_manager: FrontendManager
    runtime_manager: RuntimeManager
    template_engine: TemplateEnginePort
    strict: bool = True
    incremental: bool = False
    build_cache: Any = None
    runtime_catalog_snapshot: dict[str, Any] | None = None
    # The Project facade, exposed to extension build hooks for backward
    # compatibility. Steps should prefer the explicit collaborators above.
    project: Any = None
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("core.build")
    )
