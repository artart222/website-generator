"""Content discovery and runtime-catalog ingestion.

Extracted from the former ``Project`` god class so that "find and load source
documents" and "ingest products from a runtime snapshot" are each a single,
testable responsibility.
"""

from __future__ import annotations

import logging
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

from slugify import slugify

from processor.factory import _PROCESSOR_MAP, create_content_processor
from .build_context import BuildContext
from .page import Page

supported_extensions = list(_PROCESSOR_MAP.keys())


class RuntimeCatalogIngestor:
    """Turns a runtime catalog snapshot into generated product pages."""

    def __init__(self, ctx: BuildContext) -> None:
        self.ctx = ctx
        self.logger = logging.getLogger(__name__)

    def load_collection(
        self, collection_name: str, collection_cfg: dict, collection_path: Path | None
    ) -> None:
        ctx = self.ctx
        if ctx.runtime_catalog_snapshot is None:
            self.logger.warning(
                "No runtime catalog snapshot available for collection '%s'.", collection_name
            )
            return

        products = ctx.runtime_catalog_snapshot.get("products")
        if not isinstance(products, list):
            self.logger.warning(
                "Runtime catalog snapshot for collection '%s' does not contain products list.",
                collection_name,
            )
            return

        route_prefix = collection_cfg.get("route", {}).get("prefix", "")
        output_dir = Path(ctx.config.get("build.output_directory", "./output"))
        for product in products:
            if not isinstance(product, dict):
                continue

            page_metadata = self._normalize_product(product, collection_cfg)
            if page_metadata is None:
                continue

            page = Page(Path(), ctx.config, ctx.fs_manager)
            page.is_generated = True
            page.collection = collection_name
            page.collection_config = collection_cfg
            page.metadata = page_metadata
            page._populate_attributes()
            page.page_type = str(page_metadata.get("type", "")) or page.page_type
            page.set_route_prefix(route_prefix)
            apply_collection_defaults(page, collection_cfg)

            page.processed_content = ""
            page.raw_content = ""
            page.model_data = deepcopy(page_metadata)

            if not page.get_output_path():
                page.calculate_output_path(output_dir)

            ctx.site.add_page(page)

    def _normalize_product(
        self, product: dict[str, Any], collection_cfg: dict
    ) -> dict[str, Any] | None:
        runtime_metadata = product.get("metadata", {})
        if not isinstance(runtime_metadata, dict):
            runtime_metadata = {}

        raw_variants = product.get("variants", [])
        variants: list[dict[str, Any]] = []
        if isinstance(raw_variants, list):
            for raw_variant in raw_variants:
                if isinstance(raw_variant, dict):
                    variants.append(deepcopy(raw_variant))

        first_variant = variants[0] if variants else {}
        name = str(product.get("name", product.get("title", ""))).strip()
        if not name:
            self.logger.warning("Skipping runtime catalog product with missing name/title.")
            return None

        slug = str(product.get("slug", "")).strip() or slugify(name)
        description = str(product.get("description", "")).strip()
        summary = str(product.get("summary", description)).strip()

        sku_value = product.get("sku")
        if (sku_value is None or sku_value == "") and isinstance(first_variant, dict):
            sku_value = first_variant.get("sku", "")

        price_value = product.get("price")
        if (price_value is None or price_value == "") and isinstance(first_variant, dict):
            price_value = first_variant.get("price")

        currency_value = (
            product.get("currency")
            or (first_variant.get("currency", "") if isinstance(first_variant, dict) else "")
            or runtime_metadata.get("currency", "")
        )
        availability_value = product.get("availability", runtime_metadata.get("availability", "in_stock"))
        page_type = str(product.get("type", collection_cfg.get("model", "product"))).strip() or "product"
        layout_value = (
            product.get("layout")
            or collection_cfg.get("layout")
            or runtime_metadata.get("layout", "")
        )

        normalized = deepcopy(runtime_metadata)
        normalized["title"] = name
        normalized["slug"] = slug
        normalized["summary"] = summary
        normalized["description"] = description
        normalized["type"] = page_type
        normalized["model"] = str(collection_cfg.get("model", "product"))
        normalized["variants"] = variants
        if layout_value:
            normalized["layout"] = str(layout_value)

        if sku_value is not None and sku_value != "":
            normalized["sku"] = str(sku_value)
        if price_value is not None and price_value != "":
            normalized["price"] = price_value
        if currency_value is not None and currency_value != "":
            normalized["currency"] = str(currency_value)
        if availability_value is not None and availability_value != "":
            normalized["availability"] = str(availability_value)

        return normalized


class ContentDiscoverer:
    """Discovers source documents (and runtime catalogs) and loads them as pages."""

    def __init__(self, ctx: BuildContext) -> None:
        self.ctx = ctx
        self.logger = logging.getLogger(__name__)
        self.catalog_ingestor = RuntimeCatalogIngestor(ctx)

    def discover(self) -> None:
        ctx = self.ctx
        self.logger.info("Discovering and loading site content...")

        collections = ctx.config.get("content.collections")
        output_dir = Path(ctx.config.get("build.output_directory"))

        if isinstance(collections, dict) and collections:
            self._discover_collections(collections)
        else:
            self._discover_flat_source(output_dir)

    def _discover_collections(self, collections: dict) -> None:
        ctx = self.ctx
        collection_items: list[tuple[str, dict, Path | None]] = []
        for name, cfg in collections.items():
            if not isinstance(cfg, dict):
                continue
            path_value = cfg.get("path")
            collection_type = str(cfg.get("type", "")).strip()
            if not path_value and collection_type != "runtime_catalog":
                continue
            collection_path = Path(path_value) if path_value else None
            collection_items.append((name, cfg, collection_path))

        collection_items.sort(
            key=lambda item: len(item[2].resolve().parts) if item[2] is not None else 0,
            reverse=True,
        )

        seen_paths: set[Path] = set()
        for name, cfg, collection_path in collection_items:
            collection_type = str(cfg.get("type", "")).strip()
            if collection_type == "runtime_catalog":
                self.catalog_ingestor.load_collection(name, cfg, collection_path)
                continue

            if collection_path is None or not collection_path.exists():
                self.logger.warning("Collection path does not exist: %s", collection_path)
                continue

            page_filepaths = ctx.fs_manager.list_files(collection_path, recursive=True)
            for path in page_filepaths:
                if path in seen_paths:
                    continue
                seen_paths.add(path)

                ext = os.path.splitext(path)[1].lstrip(".").lower()
                if ext not in supported_extensions:
                    continue

                page = Page(path, ctx.config, ctx.fs_manager)
                page.collection = name
                page.collection_config = cfg
                page.set_route_prefix(cfg.get("route", {}).get("prefix", ""))

                ctx.plugin_manager.run_hook(
                    "before_page_parsed",
                    site=ctx.site,
                    config=ctx.config,
                    fs_manager=ctx.fs_manager,
                    page=page,
                )

                processor = create_content_processor(ext)
                page.load(processor)
                apply_collection_defaults(page, cfg)

                if page.draft:
                    self.logger.info("Skipping draft page: %s", page.source_filepath)
                    continue

                ctx.site.add_page(page)

                ctx.plugin_manager.run_hook(
                    "after_document_loaded",
                    site=ctx.site,
                    config=ctx.config,
                    fs_manager=ctx.fs_manager,
                    page=page,
                )
                ctx.plugin_manager.run_hook(
                    "after_page_parsed",
                    site=ctx.site,
                    config=ctx.config,
                    fs_manager=ctx.fs_manager,
                    page=page,
                )

    def _discover_flat_source(self, output_dir: Path) -> None:
        ctx = self.ctx
        content_path = Path(ctx.config.get("content.source_directory"))
        if not content_path.exists():
            self.logger.warning("Source directory does not exist: %s", content_path)
            return

        page_filepaths = ctx.fs_manager.list_files(content_path, recursive=True)
        for path in page_filepaths:
            ext = os.path.splitext(path)[1].lstrip(".").lower()
            if ext not in supported_extensions:
                continue

            page = Page(path, ctx.config, ctx.fs_manager)
            ctx.plugin_manager.run_hook(
                "before_page_parsed",
                site=ctx.site,
                config=ctx.config,
                fs_manager=ctx.fs_manager,
                page=page,
            )

            processor = create_content_processor(ext)
            page.load(processor)
            if page.draft:
                continue

            if not page.get_output_path():
                page.calculate_output_path(output_dir)

            ctx.site.add_page(page)
            ctx.plugin_manager.run_hook(
                "after_document_loaded",
                site=ctx.site,
                config=ctx.config,
                fs_manager=ctx.fs_manager,
                page=page,
            )
            ctx.plugin_manager.run_hook(
                "after_page_parsed",
                site=ctx.site,
                config=ctx.config,
                fs_manager=ctx.fs_manager,
                page=page,
            )


def apply_collection_defaults(page: Page, collection_cfg: dict) -> None:
    """Apply collection-level defaults (route prefix, type, layout) to a page."""
    page.set_route_prefix(collection_cfg.get("route", {}).get("prefix", ""))

    defaults = collection_cfg.get("defaults", {})
    if not isinstance(defaults, dict):
        defaults = {}

    if not page.page_type:
        collection_type = collection_cfg.get("type") or defaults.get("type")
        if collection_type:
            page.set_page_type(str(collection_type))

    if not page.layout:
        layout = (
            page.metadata.get("layout")
            or collection_cfg.get("layout")
            or defaults.get("layout")
            or page.metadata.get("template")
        )
        if layout:
            page.layout = str(layout[0] if isinstance(layout, list) else layout)

    if not page.layout_options and isinstance(defaults.get("layout_options"), dict):
        page.layout_options = deepcopy(defaults.get("layout_options", {}))
