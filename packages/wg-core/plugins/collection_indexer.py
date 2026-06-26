from __future__ import annotations

from pathlib import Path

from core.page import Page
from core.site import Site
from core.config import Config
from utils.fs_manager import FileSystemManager
from .base_plugin import BasePlugin


class CollectionIndexerPlugin(BasePlugin):
    """Generates synthetic index pages for collections with index config enabled."""

    def after_collections_loaded(self, **kwargs) -> None:
        self._generate_indexes(**kwargs)

    def after_pages_discovered(self, **kwargs) -> None:
        # Legacy hook support while the repo migrates.
        self._generate_indexes(**kwargs)

    def _generate_indexes(self, **kwargs) -> None:
        site: Site = kwargs["site"]
        config: Config = kwargs["config"]
        fs_manager: FileSystemManager = kwargs["fs_manager"]

        collections = config.get("content.collections", config.get("collections", {}))
        if not isinstance(collections, dict) or not collections:
            return

        output_dir = Path(config.get("build.output_directory", config.get("output_directory")))
        existing_indexes = {
            page.collection
            for page in site.get_pages()
            if getattr(page, "is_collection_index", False)
        }

        for name, cfg in collections.items():
            if not isinstance(cfg, dict):
                continue

            index_cfg = cfg.get("index", {})
            if not isinstance(index_cfg, dict) or not index_cfg.get("enabled", False):
                continue

            if name in existing_indexes:
                continue

            collection_pages = [
                p
                for p in site.get_pages()
                if getattr(p, "collection", None) == name
                and not getattr(p, "is_collection_index", False)
                and not p.draft
            ]
            collection_pages.sort(key=lambda page: page.date or "", reverse=True)

            list_items = "\n".join(
                self._render_collection_item(p)
                for p in collection_pages
            )
            html_list = f"<ul class='collection-index__list'>{list_items}</ul>"

            index_page = Page(
                source_filepath=Path("__generated__") / f"{name}-index.md",
                config=config,
                fs_manager=fs_manager,
            )
            index_page.is_generated = True
            index_page.is_collection_index = True
            index_page.collection = name
            index_page.collection_config = cfg
            index_page.add_metadata(
                {
                    "title": index_cfg.get("title", f"{name.title()} Index"),
                    "type": f"{name}-index",
                    "layout": index_cfg.get("layout", "collection"),
                    "description": index_cfg.get("description", ""),
                }
            )
            index_page.set_page_type(f"{name}-index")
            index_page.set_processed_content(html_list)
            index_page.set_route_prefix(cfg.get("route", {}).get("prefix", name))

            output_path_value = index_cfg.get("output_path")
            if output_path_value:
                output_path = Path(output_path_value)
                if output_path.suffix.lower() != ".html":
                    output_path = output_path / "index.html"
                index_page.set_output_path(output_dir / output_path)

            site.add_page(index_page)

    def _render_collection_item(self, page: Page) -> str:
        summary_html = f"<p>{page.summary}</p>" if page.summary else ""
        meta_html = self._render_collection_meta(page)
        details_url = page.get_root_rel_url()
        actions_html = (
            "<div class='collection-index__actions'>"
            f"<a class='collection-index__action' href='{details_url}'>View details</a>"
            f"<a class='collection-index__action collection-index__action--secondary' href='{details_url}#purchase-panel'>Buy now</a>"
            "</div>"
        )

        return (
            "<li class='collection-index__item'>"
            "<article>"
            f"<a href='{details_url}'>{page.title}</a>"
            f"{summary_html}"
            f"{meta_html}"
            f"{actions_html}"
            "</article>"
            "</li>"
        )

    def _render_collection_meta(self, page: Page) -> str:
        meta_parts: list[str] = []
        price = page.metadata.get("price")
        currency = str(page.metadata.get("currency", "")).strip().upper()
        availability = str(page.metadata.get("availability", "")).strip()

        price_text = self._format_price(price)
        if price_text:
            currency_label = f"{currency} " if currency else ""
            meta_parts.append(
                f"<span class='collection-index__price'>{currency_label}{price_text}</span>"
            )

        if availability:
            availability_label = availability.replace("_", " ")
            meta_parts.append(
                f"<span class='collection-index__availability'>{availability_label}</span>"
            )

        if not meta_parts:
            return ""

        return f"<div class='collection-index__meta'>{''.join(meta_parts)}</div>"

    def _format_price(self, price) -> str:
        if isinstance(price, int):
            return f"{price:,}"
        if isinstance(price, float):
            return f"{price:,.0f}" if price.is_integer() else f"{price:,.2f}"
        if isinstance(price, str) and price.strip():
            return price.strip()
        return ""
