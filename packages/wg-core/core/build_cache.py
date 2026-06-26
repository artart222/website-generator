"""Incremental build cache.

Skips re-rendering pages whose inputs have not changed since the last build.
A page's cache key is a hash of its content + metadata + resolved layout,
combined with a global *build signature* (theme tokens + site/build config). If
the build signature changes, every page is treated as stale, so theme or config
changes correctly invalidate the whole cache.

This is opt-in (``build.incremental``); the default full build is unaffected.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MANIFEST_FILENAME = ".wg-build-cache.json"


def compute_build_signature(parts: dict[str, Any]) -> str:
    """Hash the global inputs that, when changed, invalidate every page."""
    blob = json.dumps(parts, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class BuildCache:
    """Reads/writes a per-output content-hash manifest for incremental builds."""

    def __init__(self, output_dir: Path, build_signature: str) -> None:
        self.output_dir = Path(output_dir)
        self.manifest_path = self.output_dir / MANIFEST_FILENAME
        self.build_signature = build_signature
        self._previous: dict[str, str] = {}
        self._current: dict[str, str] = {}

    def load(self) -> None:
        if not self.manifest_path.exists():
            self._previous = {}
            return
        try:
            data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self._previous = {}
            return
        if not isinstance(data, dict) or data.get("signature") != self.build_signature:
            # Signature mismatch (theme/config changed) invalidates everything.
            self._previous = {}
            return
        entries = data.get("pages", {})
        self._previous = entries if isinstance(entries, dict) else {}

    def page_hash(self, *, raw_content: str, metadata: dict[str, Any], layout: str | None) -> str:
        payload = {
            "raw": raw_content,
            "metadata": metadata,
            "layout": layout,
        }
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def is_unchanged(self, key: str, page_hash: str) -> bool:
        return self._previous.get(key) == page_hash

    def record(self, key: str, page_hash: str) -> None:
        self._current[key] = page_hash

    def save(self) -> None:
        manifest = {"signature": self.build_signature, "pages": self._current}
        self.manifest_path.write_text(
            json.dumps(manifest, sort_keys=True, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
