"""Optional JSON export of the built site (for hybrid/headless frontends).

Extracted verbatim (behavior-preserving) from the former ``Project`` god class.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .build_context import BuildContext


class JsonExporter:
    """Writes ``site.json`` plus one ``page.json`` per page when enabled."""

    def __init__(self, ctx: BuildContext) -> None:
        self.ctx = ctx

    def export(self) -> None:
        ctx = self.ctx
        export_data = ctx.config.get("experimental.export_data", {})
        if not isinstance(export_data, dict) or not export_data.get("enabled", False):
            return

        output_dir = Path(ctx.config.get("build.output_directory"))
        data_dir = Path(export_data.get("output_dir", "./output/data"))
        include_collections = export_data.get("include_collections")
        filter_collections = (
            isinstance(include_collections, list) and len(include_collections) > 0
        )

        site_payload: dict = {
            "site": {
                "name": ctx.config.get("site.name", ""),
                "description": ctx.config.get("site.description", ""),
                "base_url": ctx.config.get("site.base_url", ""),
            },
            "frontend": ctx.frontend_manager.get_context().get("frontend", {}),
            "runtime": ctx.runtime_manager.build_public_config(),
            "pages": [],
        }

        for page in ctx.site.pages:
            if filter_collections and page.collection not in include_collections:
                continue

            output_path = page.get_output_path()
            if not output_path:
                continue

            try:
                rel_output_path = output_path.relative_to(output_dir)
            except ValueError:
                rel_output_path = Path(output_path.name)

            if rel_output_path.name == "index.html":
                json_rel_path = rel_output_path.parent / "page.json"
            else:
                json_rel_path = rel_output_path.with_suffix(".json")
            json_output_path = data_dir / json_rel_path

            page_payload = {
                "title": page.title,
                "slug": page.slug,
                "type": page.page_type,
                "model": page.model_name,
                "model_data": self._make_json_safe(page.model_data),
                "collection": page.collection,
                "abs_url": page.abs_url,
                "root_rel_url": page.root_rel_url,
                "metadata": self._make_json_safe(page.metadata),
                "content_html": page.processed_content,
                "blocks": self._make_json_safe(page.blocks),
                "islands": self._make_json_safe(page.islands),
                "layout": page.layout,
            }

            ctx.fs_manager.write_file(
                json_output_path,
                json.dumps(page_payload, ensure_ascii=False, indent=2, sort_keys=True),
            )

            try:
                data_rel_dir = data_dir.relative_to(output_dir)
                json_path = data_rel_dir / json_rel_path
            except ValueError:
                json_path = json_output_path

            site_payload["pages"].append(
                {
                    "title": page.title,
                    "slug": page.slug,
                    "type": page.page_type,
                    "model": page.model_name,
                    "collection": page.collection,
                    "url": page.abs_url,
                    "root_rel_url": page.root_rel_url,
                    "json_path": str(json_path).replace(os.sep, "/"),
                }
            )

        site_index_path = data_dir / "site.json"
        ctx.fs_manager.write_file(
            site_index_path,
            json.dumps(site_payload, ensure_ascii=False, indent=2, sort_keys=True),
        )

    def _make_json_safe(self, value):
        if isinstance(value, dict):
            return {str(key): self._make_json_safe(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._make_json_safe(item) for item in value]
        if isinstance(value, tuple):
            return [self._make_json_safe(item) for item in value]
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return value
