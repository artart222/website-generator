from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .routing import build_output_path, to_abs_url, to_root_relative_url


@dataclass
class Route:
    output_path: Path
    root_rel_url: str
    abs_url: str


class Router:
    """Canonical routing for output paths and public URLs.

    Routing rules live in :mod:`core.routing`; this class applies them to
    ``Page`` objects and records the result on the page.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self.output_dir = Path(self.config.get("build.output_directory"))
        self.base_url = str(self.config.get("site.base_url", "")).rstrip("/")

    def assign(self, page) -> Route:
        output_path = page.get_output_path() or self._build_output_path(page)
        page.set_output_path(output_path)

        root_rel_url = to_root_relative_url(output_path, self.output_dir)
        abs_url = to_abs_url(self.base_url, root_rel_url)

        page.set_rel_url(root_rel_url)
        page.abs_url = abs_url

        return Route(output_path=output_path, root_rel_url=root_rel_url, abs_url=abs_url)

    def _build_output_path(self, page) -> Path:
        index_cfg = page.collection_config.get("index", {}) if page.collection_config else {}
        index_output_path = str(index_cfg.get("output_path", "")) if isinstance(index_cfg, dict) else ""
        return build_output_path(
            self.output_dir,
            is_home=page.is_home_page(),
            is_not_found=page.is_not_found_page(),
            is_collection_index=getattr(page, "is_collection_index", False),
            route_prefix=page.get_route_prefix(),
            slug=page.slug,
            collection=page.collection,
            index_output_path=index_output_path,
        )
