from __future__ import annotations

import logging
from typing import Any, Iterator

from slugify import slugify

from .config import Config
from .page import Page


class Site:
    """In-memory site model used across the build."""

    def __init__(self, config: Config) -> None:
        self.logger = logging.getLogger(__name__)
        self.config: Config = config

        self.name: str = str(config.get("site.name", config.get("site_name", "Website Generator")))
        self.base_url: str = str(config.get("site.base_url", config.get("base_url", "/")))
        self.pages: list[Page] = []
        self.header = ""
        self.data: dict[str, Any] = {}
        self.navigation_items: list[dict[str, Any]] = []

    def add_page(self, page: Page) -> None:
        self.pages.append(page)
        self.logger.debug("Page '%s' added to site.", page.source_filepath)

    def set_data(self, data: dict[str, Any]) -> None:
        self.data = data

    def get_pages(self) -> list[Page]:
        return self.pages

    def get_page_by_url(self, url: str) -> Page | None:
        for page in self.pages:
            if page.abs_url == url:
                return page
        return None

    def get_page_by_type(self, page_type: str) -> list[Page]:
        return [page for page in self.pages if page_type in page.get_page_type()]

    def get_collection_index_page(self, collection_name: str) -> Page | None:
        for page in self.pages:
            if getattr(page, "is_collection_index", False) and page.collection == collection_name:
                return page
        return None

    def build_navigation(self) -> list[dict[str, Any]]:
        nav_config = self.config.get("site.navigation", self.config.get("navigation", []))
        if not isinstance(nav_config, list):
            nav_config = []

        navigation_items: list[dict[str, Any]] = []
        for raw_item in nav_config:
            if not isinstance(raw_item, dict):
                continue

            title = str(raw_item.get("title", "")).strip()
            url = self._resolve_navigation_url(raw_item)
            if not title or not url:
                continue

            navigation_items.append(
                {
                    "title": title,
                    "url": url,
                    "key": slugify(title),
                    "is_external": str(url).startswith(("http://", "https://")),
                }
            )

        self.navigation_items = navigation_items
        self.header = self.populate_header()
        return navigation_items

    def _resolve_navigation_url(self, raw_item: dict[str, Any]) -> str:
        url = raw_item.get("url")
        if url:
            return str(url)

        collection_index = raw_item.get("collection_index")
        if collection_index:
            page = self.get_collection_index_page(str(collection_index))
            return page.get_root_rel_url() if page else ""

        page_type = raw_item.get("type")
        if page_type:
            candidates = self.get_page_by_type(str(page_type))
            if candidates:
                return candidates[0].get_root_rel_url()

        collection_name = raw_item.get("collection")
        if collection_name:
            page = self.get_collection_index_page(str(collection_name))
            if page:
                return page.get_root_rel_url()

        return ""

    def populate_header(self) -> str:
        if not self.navigation_items:
            self.build_navigation()

        return "\n".join(
            f"<li><a href='{item['url']}'>{item['title']}</a></li>"
            for item in self.navigation_items
        )

    def __iter__(self) -> Iterator[Page]:
        return iter(self.pages)

    def __repr__(self) -> str:
        return f"<Site name='{self.name}' pages={len(self.pages)}>"

    def __len__(self) -> int:
        return len(self.pages)
