"""Composition root for a build.

This is the one place that decides which concrete infrastructure adapters are
wired into the build. Application code depends on ports
(:mod:`wg_contracts.ports`); only here do we choose the concrete
``FileSystemManager``, Django template engine, etc. Tests can call
:func:`build_project` with fakes to exercise the pipeline in isolation.
"""

from __future__ import annotations

from typing import Callable

from engines.base_engine import TemplateEngine
from engines.factory import create_template_engine
from wg_contracts.ports import FileSystemPort
from .config import Config
from .project import Project


def build_project(
    config: Config,
    *,
    fs_manager: FileSystemPort | None = None,
    template_engine_factory: Callable[[str, list[str]], TemplateEngine] = create_template_engine,
) -> Project:
    """Construct a fully wired :class:`Project` from configuration."""
    return Project(
        config,
        fs_manager=fs_manager,
        template_engine_factory=template_engine_factory,
    )
