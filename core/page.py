from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

from slugify import slugify

from processor.base_processor import ContentProcessor
from utils.fs_manager import FileSystemManager
from .config import Config

if TYPE_CHECKING:
    from .site import Site


class Page:
    """Represents a source document or generated page in the build."""

    def __init__(
        self,
        source_filepath,
        config: Config,
        fs_manager: Optional[FileSystemManager],
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.config: Config = config
        self.source_filepath: Path = Path(source_filepath) if source_filepath else Path()
        self.fs_manager: FileSystemManager | None = fs_manager

        self.raw_content: str = ""
        self.processed_content: str = ""
        self.metadata: dict[str, Any] = {}
        self.title: str = ""
        self.slug: str = ""
        self.page_type: str | None = None
        self.summary: str = ""
        self.description: str = ""
        self.author: list[str] = []
        self.keywords: list[str] = []
        self.tags: list[str] = []
        self.categories: list[str] = []
        self.date: str = ""
        self.draft: bool = False
        self.image: str = ""
        self.collection: str | None = None
        self.collection_config: dict | None = None
        self.layout: str | None = None
        self.layout_options: dict[str, Any] = {}
        self.blocks: list[dict[str, Any]] = []
        self.islands: list[dict[str, Any]] = []
        self.route_prefix: str = ""
        self.is_generated: bool = False
        self.is_collection_index: bool = False
        self.model_name: str | None = None
        self.model_data: dict[str, Any] = {}
        self.validation_errors: list[str] = []

        self.output_path: Path | None = None
        self.abs_url: str = ""
        self.root_rel_url: str = ""

    def read_source_file(self) -> None:
        if self.fs_manager is not None and self.source_filepath.is_file():
            self.raw_content = self.fs_manager.read_file(self.source_filepath)
        else:
            self.raw_content = ""

    def process_content(self, content_processor: ContentProcessor | None) -> None:
        if content_processor:
            self.processed_content = content_processor.process(self.raw_content)
        else:
            self.processed_content = self.raw_content

    def process_metadata(self, content_processor: ContentProcessor | None) -> None:
        if content_processor:
            self.metadata = content_processor.get_metadata()
        else:
            self.metadata = {}
        self._populate_attributes()

    def load(self, content_processor: ContentProcessor | None) -> None:
        self.logger.debug("Loading page from: %s", self.source_filepath)
        if self.fs_manager is not None and self.source_filepath.is_file():
            self.raw_content = self.fs_manager.read_file(self.source_filepath)
        else:
            self.raw_content = ""

        if content_processor:
            self.processed_content = content_processor.process(self.raw_content)
            metadata = content_processor.get_metadata()
            self.metadata = metadata if isinstance(metadata, dict) else {}
        else:
            self.processed_content = self.raw_content
            self.metadata = {}

        self._populate_attributes()

    def _populate_attributes(self) -> None:
        default_title = (
            os.path.splitext(os.path.basename(self.source_filepath))[0]
            if str(self.source_filepath)
            else "Generated Page"
        )

        self.title = str(self._first_value("title", default_title))
        self.summary = str(self._first_value("summary", ""))
        self.description = str(
            self._first_value("description", self._first_value("summary", ""))
        )
        self.slug = slugify(str(self._first_value("slug", self.title or default_title)))

        page_type_value = self._first_value("type", None)
        self.page_type = str(page_type_value) if page_type_value else self.page_type

        self.author = self._ensure_string_list(
            self.metadata.get("authors", self.metadata.get("author", []))
        )
        self.keywords = self._ensure_string_list(self.metadata.get("keywords", []))
        self.tags = self._ensure_string_list(self.metadata.get("tags", []))
        self.categories = self._ensure_string_list(self.metadata.get("categories", []))
        self.date = str(self._first_value("date", ""))
        self.draft = self._ensure_bool(self._first_value("draft", False))
        self.image = self.ensure_image_url_is_safe()

        layout_value = self._first_value("layout", self._first_value("template", None))
        self.layout = str(layout_value) if layout_value else self.layout

        layout_options = self.metadata.get("layout_options", {})
        self.layout_options = layout_options if isinstance(layout_options, dict) else {}

        blocks = self.metadata.get("blocks", [])
        self.blocks = blocks if isinstance(blocks, list) else []
        islands = self.metadata.get("islands", [])
        self.islands = islands if isinstance(islands, list) else []

        self.logger.debug(
            "Page attributes populated for '%s': slug=%s type=%s layout=%s",
            self.title,
            self.slug,
            self.page_type,
            self.layout,
        )

    def _first_value(self, key: str, default: Any = None) -> Any:
        value = self.metadata.get(key, default)
        if isinstance(value, list):
            if len(value) == 1:
                return value[0]
            return value
        return value

    def _ensure_string_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return [str(value)]

    def _ensure_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes", "on"}
        return bool(value)

    def get_output_path_without_output_dir(self, output_dir: Path | str) -> Path:
        output_root = Path(output_dir)
        if self.output_path and self.output_path.is_relative_to(output_root):
            return self.output_path.relative_to(output_root)
        return self.output_path or Path()

    def generate_abs_url(self) -> str:
        base_url = str(
            self.config.get("site.base_url", self.config.get("base_url", ""))
        ).rstrip("/")
        if not self.root_rel_url:
            self.generate_root_rel_url()

        self.abs_url = f"{base_url}{self.root_rel_url}" if base_url else self.root_rel_url
        return self.abs_url

    def generate_root_rel_url(self) -> str:
        if not self.output_path:
            self.root_rel_url = "/"
            return self.root_rel_url

        rel_path = self.get_output_path_without_output_dir(
            self.config.get("build.output_directory", self.config.get("output_directory", "./output"))
        )
        rel_path_str = str(rel_path).replace(os.sep, "/")

        if rel_path_str == "index.html":
            self.root_rel_url = "/"
            return self.root_rel_url

        if rel_path_str.endswith("/index.html"):
            self.root_rel_url = "/" + rel_path_str[: -len("index.html")]
            return self.root_rel_url

        self.root_rel_url = "/" + rel_path_str
        return self.root_rel_url

    def calculate_output_path(
        self, output_dir: Path, url_prefix: str | None = None
    ) -> Path:
        prefix = url_prefix if url_prefix is not None else self.get_route_prefix()

        if self.is_home_page():
            self.output_path = output_dir / "index.html"
            return self.output_path

        if self.is_not_found_page():
            self.output_path = output_dir / "404.html"
            return self.output_path

        folder_path = output_dir
        if prefix:
            folder_path = folder_path / slugify(prefix)
        if self.slug:
            folder_path = folder_path / slugify(self.slug)

        self.output_path = folder_path / "index.html"
        return self.output_path

    def set_raw_content(self, content: str) -> None:
        self.raw_content = content

    def set_processed_content(self, content: str) -> None:
        self.processed_content = content

    def add_metadata(self, inp: dict[str, Any]) -> None:
        self.metadata.update(inp)
        self._populate_attributes()

    def set_slug(self) -> None:
        slug_source = self._first_value("slug", self.title)
        self.slug = slugify(str(slug_source))

    def set_title(self) -> None:
        default_title = (
            os.path.splitext(os.path.basename(self.source_filepath))[0]
            if str(self.source_filepath)
            else "Generated Page"
        )
        self.title = str(self._first_value("title", default_title))

    def set_page_type(self, page_type: str) -> None:
        self.page_type = page_type

    def set_output_path(self, output_path: Path) -> None:
        self.output_path = output_path

    def get_context(
        self,
        header: str,
        site: Site | None = None,
        stylesheets: Optional[list[str]] = None,
        scripts: Optional[list[str]] = None,
        navigation_items: Optional[list[dict[str, Any]]] = None,
        theme_context: Optional[dict[str, Any]] = None,
        rendered_blocks: str = "",
        layout_options: Optional[dict[str, Any]] = None,
        frontend_context: Optional[dict[str, Any]] = None,
        runtime_context: Optional[dict[str, Any]] = None,
        extensions_context: Optional[dict[str, Any]] = None,
    ) -> dict:
        theme_context = theme_context or {}
        layout_options = layout_options or {}
        frontend_context = frontend_context or {}
        runtime_context = runtime_context or {}
        extensions_context = extensions_context or {}

        return {
            "content": self.processed_content,
            "rendered_blocks": rendered_blocks,
            "page_title": self.get_title(),
            "page_summary": self.summary,
            "page_description": self.get_page_description(),
            "page_keywords": self.keywords,
            "page_authors": self.author,
            "page_tags": self.tags,
            "page_categories": self.categories,
            "page_date": self.date,
            "page_draft": self.draft,
            "site_name": self.config.get("site.name", self.config.get("site_name", "Website Generator")),
            "page_url": self.get_abs_url(),
            "page_image": self.metadata.get("image", "/assets/default-share.png"),
            "page_type": self.page_type,
            "page_layout": self.layout,
            "page_layout_options": layout_options,
            "page_blocks": self.blocks,
            "page_islands": self.islands,
            "page_frontend_islands": self.islands,
            "page_meta": self.metadata,
            "page_model_name": self.model_name,
            "page_model": self.model_data,
            "page_price_display": self._format_price_display(
                self.model_data.get("price", self.metadata.get("price"))
            ),
            "page_compare_price_display": self._format_price_display(
                self.model_data.get(
                    "price_compare_at", self.metadata.get("price_compare_at")
                )
            ),
            "page_currency": str(
                self.model_data.get("currency", self.metadata.get("currency", ""))
            ),
            "page_availability_label": str(
                self.model_data.get(
                    "availability", self.metadata.get("availability", "")
                )
            ).replace("_", " "),
            "page_validation_errors": self.validation_errors,
            "page": self,
            "site": site,
            "site_data": site.data if site else {},
            "header": header,
            "navigation_items": navigation_items or [],
            "stylesheets": stylesheets or [],
            "scripts": scripts or [],
            "body_class": "",
            "container_class": "",
            "collection": self.collection,
            "collection_config": self.collection_config,
            "theme": theme_context.get("theme_name"),
            "theme_manifest": theme_context.get("theme_manifest", {}),
            "theme_settings": theme_context.get("theme_settings", {}),
            "theme_tokens": theme_context.get("theme_tokens", {}),
            "theme_component_presets": theme_context.get(
                "theme_component_presets", {}
            ),
            "core_blocks": theme_context.get("core_blocks", []),
            "frontend": frontend_context.get("frontend", {}),
            "runtime": runtime_context.get("runtime", {}),
            "extensions": extensions_context.get("extensions", {}),
        }

    def set_rel_url(self, rel_url: str) -> None:
        self.root_rel_url = rel_url

    def get_title(self) -> str:
        return self.title

    def get_page_description(self) -> str:
        return self.description

    def get_metadata(self) -> dict:
        return self.metadata

    def get_page_type(self) -> list[str]:
        if isinstance(self.page_type, list):
            return self.page_type
        if self.page_type is None:
            return []
        return [self.page_type]

    def get_source_filepath(self) -> Path:
        return self.source_filepath

    def get_slug(self) -> str:
        return self.slug

    def get_output_path(self) -> Path | None:
        return self.output_path

    def get_abs_url(self) -> str:
        return self.abs_url

    def get_root_rel_url(self) -> str:
        return self.root_rel_url

    def get_route_prefix(self) -> str:
        if self.route_prefix:
            return self.route_prefix
        if isinstance(self.collection_config, dict):
            route = self.collection_config.get("route", {})
            if isinstance(route, dict):
                return str(route.get("prefix", ""))
        return ""

    def set_route_prefix(self, route_prefix: str) -> None:
        self.route_prefix = route_prefix

    def is_home_page(self) -> bool:
        return self.page_type in {"index", "home"} or self.slug in {"index", "home"}

    def is_not_found_page(self) -> bool:
        return self.page_type == "404" or self.slug == "404"

    def ensure_image_url_is_safe(self) -> str:
        image_addr: Any = self.metadata.get("image")

        if isinstance(image_addr, list):
            return str(image_addr[0]) if image_addr else "/assets/default-share.png"

        if isinstance(image_addr, str) and image_addr:
            return image_addr

        return "/assets/default-share.png"

    def _format_price_display(self, value: Any) -> str:
        if value is None or value == "":
            return ""
        if isinstance(value, bool):
            return str(value)
        if isinstance(value, int):
            return f"{value:,}"
        if isinstance(value, float):
            return f"{value:,.0f}" if value.is_integer() else f"{value:,.2f}"
        if isinstance(value, str):
            return value.strip()
        return str(value)

    def __repr__(self) -> str:
        return f"<Page title='{self.title}' slug='{self.slug}' type='{self.page_type}'>"
