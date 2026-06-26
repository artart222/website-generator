"""Ports (interfaces) for the static-site generator core.

The SSG application layer depends on these abstractions, never on concrete
infrastructure. Infrastructure adapters (local filesystem, Django templates,
Markdown, HTTP catalog) implement them, and the composition root wires the
concretes in. This is the Dependency Inversion Principle in practice.

They are defined as ``typing.Protocol`` so existing concrete classes satisfy
them structurally without needing to inherit, which keeps the refactor
incremental and low-risk.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class FileSystemPort(Protocol):
    """Filesystem operations the build depends on."""

    def read_file(self, filepath: Path) -> str: ...

    def write_file(self, filepath: Path, content: str) -> None: ...

    def copy_file(self, source_path: Path, dest_path: Path) -> None: ...

    def copy_directory(
        self, source_dir: Path, dest_dir: Path, exist_ok: bool = False
    ) -> None: ...

    def create_directory(self, dir_path: Path, exist_ok: bool = True) -> None: ...

    def list_files(
        self,
        directory: Path,
        recursive: bool = False,
        extensions: Optional[list[str]] = None,
    ) -> list[Path]: ...

    def path_exists(self, path: Path) -> bool: ...


@runtime_checkable
class TemplateEnginePort(Protocol):
    """Renders templates by name or from a string."""

    def render(self, template_name: str, context: dict) -> str: ...

    def render_from_string(self, template_string: str, context: dict) -> str: ...


@runtime_checkable
class ContentProcessorPort(Protocol):
    """Converts raw source content into HTML and extracts metadata."""

    def process(self, raw_content: str) -> str: ...

    def get_metadata(self) -> dict: ...


@runtime_checkable
class CatalogSourcePort(Protocol):
    """Provides a product catalog snapshot for runtime-backed collections.

    This is the seam that keeps wg-core independent of the Django runtime: the
    HTTP implementation lives in infrastructure, while the build only knows this
    interface.
    """

    def fetch_snapshot(self) -> dict[str, Any] | None: ...


@runtime_checkable
class ClockPort(Protocol):
    """Supplies the current time/date (injectable for deterministic tests)."""

    def today_iso(self) -> str: ...
