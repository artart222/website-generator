"""Single source of truth for output-path and URL computation.

Both :class:`core.router.Router` and the thin compatibility methods on
:class:`core.page.Page` delegate here, so the path/URL rules exist in exactly
one place instead of being duplicated (and silently drifting) across the two.
"""

from __future__ import annotations

import os
from pathlib import Path

from slugify import slugify


def build_output_path(
    output_dir: Path,
    *,
    is_home: bool = False,
    is_not_found: bool = False,
    is_collection_index: bool = False,
    route_prefix: str = "",
    slug: str = "",
    collection: str | None = None,
    index_output_path: str = "",
) -> Path:
    """Compute the output HTML path for a page."""
    if is_not_found:
        return output_dir / "404.html"

    if is_home:
        return output_dir / "index.html"

    if is_collection_index:
        if index_output_path:
            candidate = Path(index_output_path)
            if candidate.suffix.lower() != ".html":
                candidate = candidate / "index.html"
            return output_dir / candidate
        if route_prefix:
            return output_dir / slugify(route_prefix) / "index.html"
        return output_dir / slugify(collection or "index") / "index.html"

    segments: list[str] = []
    if route_prefix:
        segments.append(slugify(route_prefix))
    if slug:
        segments.append(slugify(slug))

    if not segments:
        return output_dir / "index.html"

    return output_dir.joinpath(*segments) / "index.html"


def to_root_relative_url(output_path: Path | None, output_dir: Path) -> str:
    """Convert an output path into a root-relative URL such as ``/blog/post/``."""
    if not output_path:
        return "/"

    output_root = Path(output_dir)
    try:
        rel_path = output_path.relative_to(output_root)
    except ValueError:
        # Path is not under the output directory; fall back to its name.
        rel_path = Path(output_path.name)

    rel_path_str = str(rel_path).replace(os.sep, "/")

    if rel_path_str == "index.html":
        return "/"
    if rel_path_str.endswith("/index.html"):
        return "/" + rel_path_str[: -len("index.html")]
    if rel_path_str.endswith("index.html"):
        return "/" + rel_path_str[: -len("index.html")]
    return "/" + rel_path_str


def to_abs_url(base_url: str, root_rel_url: str) -> str:
    """Join a (possibly empty) base URL with a root-relative URL."""
    normalized_base = str(base_url).rstrip("/")
    return f"{normalized_base}{root_rel_url}" if normalized_base else root_rel_url
