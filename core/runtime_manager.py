from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from utils.fs_manager import FileSystemManager


class RuntimeManager:
    """Serializes runtime target configuration into public build artifacts."""

    def __init__(self, config, fs_manager: FileSystemManager, extension_manager) -> None:
        self.config = config
        self.fs_manager = fs_manager
        self.extension_manager = extension_manager
        self.public_manifest: dict[str, Any] = {"targets": [], "integrations": {}}

    def build_public_config(self) -> dict[str, Any]:
        runtime_cfg = self.config.get("runtime", {})
        integrations_cfg = self.config.get("integrations", {})
        targets = runtime_cfg.get("targets", []) if isinstance(runtime_cfg, dict) else []
        if not isinstance(targets, list):
            targets = []

        public_targets: list[dict[str, Any]] = []
        for raw_target in targets:
            if not isinstance(raw_target, dict):
                continue
            public_target = {
                "name": str(raw_target.get("name", "")),
                "type": str(raw_target.get("type", "")),
                "public_base_url": str(raw_target.get("public_base_url", "")),
                "capabilities": deepcopy(raw_target.get("capabilities", []))
                if isinstance(raw_target.get("capabilities", []), list)
                else [],
            }
            public_targets.append(public_target)

        public_integrations = deepcopy(integrations_cfg) if isinstance(integrations_cfg, dict) else {}
        payment_providers = public_integrations.get("payments", {}).get("providers", {})
        if isinstance(payment_providers, dict):
            for _, provider_cfg in payment_providers.items():
                if not isinstance(provider_cfg, dict):
                    continue
                adapter_name = str(provider_cfg.get("adapter", ""))
                adapter_metadata = self.extension_manager.runtime_adapter_registry.describe(adapter_name)
                if adapter_metadata:
                    provider_cfg["adapter_metadata"] = adapter_metadata
                provider_cfg.pop("secret", None)
                provider_cfg.pop("api_key", None)

        self.public_manifest = {
            "targets": public_targets,
            "integrations": public_integrations,
        }
        return self.public_manifest

    def fetch_catalog_snapshot(self) -> tuple[dict[str, Any] | None, Path | None]:
        runtime_cfg = self.config.get("runtime", {})
        if not isinstance(runtime_cfg, dict):
            return None, None

        snapshot_cfg = runtime_cfg.get("catalog_snapshot", {})
        if not isinstance(snapshot_cfg, dict) or not snapshot_cfg.get("enabled", False):
            return None, None

        targets = runtime_cfg.get("targets", [])
        if not isinstance(targets, list):
            targets = []

        target_name = str(snapshot_cfg.get("target", "")).strip()
        target = None
        if target_name:
            for raw_target in targets:
                if isinstance(raw_target, dict) and str(raw_target.get("name", "")).strip() == target_name:
                    target = raw_target
                    break
        if target is None and targets:
            first_target = targets[0]
            if isinstance(first_target, dict):
                target = first_target

        if not isinstance(target, dict):
            return None, None

        public_base_url = str(target.get("public_base_url", "")).strip()
        if not public_base_url:
            return None, None

        url_path = str(snapshot_cfg.get("url_path", "/catalog/snapshot")).strip()
        if not url_path.startswith("/"):
            url_path = "/" + url_path

        snapshot_url = urljoin(public_base_url.rstrip("/") + "/", url_path.lstrip("/"))
        request = Request(snapshot_url, headers={"Accept": "application/json"})

        try:
            with urlopen(request, timeout=30) as response:
                payload = response.read()
                snapshot_data = json.loads(payload.decode("utf-8"))
        except (HTTPError, URLError, ValueError, json.JSONDecodeError):
            return None, None

        output_dir = Path(snapshot_cfg.get("output_dir", "./output/data/runtime"))
        self.fs_manager.create_directory(output_dir)
        output_path = output_dir / "catalog.json"
        self.fs_manager.write_file(
            output_path,
            json.dumps(snapshot_data, ensure_ascii=False, indent=2, sort_keys=True),
        )
        return snapshot_data, output_path

    def get_context(self) -> dict[str, Any]:
        configured_targets = self.config.get("runtime.targets", [])
        if not isinstance(configured_targets, list):
            configured_targets = []
        public_manifest = self.build_public_config()
        output_dir = Path(
            self.config.get("build.output_directory", self.config.get("output_directory"))
        )
        runtime_output_dir = output_dir / "runtime"
        self.fs_manager.create_directory(runtime_output_dir)
        manifest_json = json.dumps(
            public_manifest,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        self.fs_manager.write_file(runtime_output_dir / "manifest.json", manifest_json)
        self.fs_manager.write_file(runtime_output_dir / "public-config.json", manifest_json)

        has_targets = bool(public_manifest.get("targets")) or bool(configured_targets)
        return {
            "runtime": {
                "targets": deepcopy(
                    public_manifest.get("targets", [])
                    or configured_targets
                ),
                "manifest_url": "/runtime/manifest.json"
                if has_targets
                else "",
            }
        }

    def emit_manifest(self) -> dict[str, Any]:
        return self.get_context()
