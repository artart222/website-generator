from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from slugify import slugify

from .config import Config


@dataclass
class Route:
    output_path: Path
    root_rel_url: str
    abs_url: str


class Router:
    """Canonical routing for output paths and public URLs."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.output_dir = Path(
            self.config.get("build.output_directory", self.config.get("output_directory"))
        )
        self.base_url = str(
            self.config.get("site.base_url", self.config.get("base_url", ""))
        ).rstrip("/")

    def assign(self, page) -> Route:
        output_path = page.get_output_path() or self._build_output_path(page)
        page.set_output_path(output_path)

        root_rel_url = self._to_root_relative_url(output_path)
        abs_url = f"{self.base_url}{root_rel_url}" if self.base_url else root_rel_url

        page.set_rel_url(root_rel_url)
        page.abs_url = abs_url

        return Route(output_path=output_path, root_rel_url=root_rel_url, abs_url=abs_url)

    def _build_output_path(self, page) -> Path:
        if page.is_not_found_page():
            return self.output_dir / "404.html"

        if page.is_home_page():
            return self.output_dir / "index.html"

        if getattr(page, "is_collection_index", False):
            index_cfg = page.collection_config.get("index", {}) if page.collection_config else {}
            output_path_value = index_cfg.get("output_path")
            if output_path_value:
                output_path = Path(output_path_value)
                if output_path.suffix.lower() != ".html":
                    output_path = output_path / "index.html"
                return self.output_dir / output_path

            prefix = page.get_route_prefix()
            if prefix:
                return self.output_dir / slugify(prefix) / "index.html"
            return self.output_dir / slugify(page.collection or "index") / "index.html"

        route_segments: list[str] = []
        prefix = page.get_route_prefix()
        if prefix:
            route_segments.append(slugify(prefix))
        if page.slug:
            route_segments.append(slugify(page.slug))

        if not route_segments:
            return self.output_dir / "index.html"

        return self.output_dir.joinpath(*route_segments) / "index.html"

    def _to_root_relative_url(self, output_path: Path) -> str:
        rel_path = output_path.relative_to(self.output_dir)
        rel_path_str = str(rel_path).replace(os.sep, "/")

        if rel_path_str == "index.html":
            return "/"

        if rel_path_str.endswith("/index.html"):
            return "/" + rel_path_str[: -len("index.html")]

        if rel_path_str.endswith("index.html"):
            return "/" + rel_path_str[: -len("index.html")]

        return "/" + rel_path_str
