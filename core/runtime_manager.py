from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

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

    def emit_manifest(self) -> dict[str, Any]:
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
        return public_manifest

    def get_context(self) -> dict[str, Any]:
        configured_targets = self.config.get("runtime.targets", [])
        if not isinstance(configured_targets, list):
            configured_targets = []
        has_targets = bool(self.public_manifest.get("targets")) or bool(configured_targets)
        return {
            "runtime": {
                "targets": deepcopy(
                    self.public_manifest.get("targets", [])
                    or configured_targets
                ),
                "manifest_url": "/runtime/manifest.json"
                if has_targets
                else "",
            }
        }
