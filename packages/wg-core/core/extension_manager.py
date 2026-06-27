from __future__ import annotations

from copy import deepcopy
import importlib
import inspect
import logging
from importlib import metadata
from pathlib import Path
from typing import Any, Callable

import yaml
from slugify import slugify

from utils.fs_manager import FileSystemManager
from .content_models import ContentModelRegistry, DEFAULT_MODELS


class DefinitionRegistry:
    """Simple named registry for extension-provided objects."""

    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}

    def register(self, name: str, value: Any, *, metadata: dict[str, Any] | None = None) -> None:
        self._items[str(name)] = {
            "value": value,
            "metadata": deepcopy(metadata or {}),
        }

    def get(self, name: str, default: Any = None) -> Any:
        entry = self._items.get(str(name))
        return default if entry is None else entry["value"]

    def describe(self, name: str) -> dict[str, Any]:
        entry = self._items.get(str(name), {})
        metadata_value = entry.get("metadata", {})
        return deepcopy(metadata_value if isinstance(metadata_value, dict) else {})

    def names(self) -> list[str]:
        return list(self._items.keys())


class BuildHookRegistry:
    """Stores extension build hooks keyed by lifecycle name."""

    def __init__(self) -> None:
        self._hooks: dict[str, list[Callable[..., Any]]] = {}

    def register(self, hook_name: str, func: Callable[..., Any]) -> None:
        self._hooks.setdefault(str(hook_name), []).append(func)

    def run(self, hook_name: str, **kwargs) -> list[Any]:
        results: list[Any] = []
        for func in self._hooks.get(str(hook_name), []):
            results.append(func(**kwargs))
        return results


class CommandRegistry:
    """Stores extension CLI commands for future CLI integration."""

    def __init__(self) -> None:
        self._commands: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, func: Callable[..., Any]) -> None:
        self._commands[str(name)] = func

    def get(self, name: str) -> Callable[..., Any] | None:
        return self._commands.get(str(name))


class ExtensionAPI:
    """Mutable registries passed into extension registration hooks."""

    def __init__(self) -> None:
        self.models = ContentModelRegistry()
        self.frontend_targets = DefinitionRegistry()
        self.runtime_adapters = DefinitionRegistry()
        self.build_hooks = BuildHookRegistry()
        self.commands = CommandRegistry()


class ExtensionLoadError(RuntimeError):
    """Raised when an extension cannot be loaded."""


class LoadedExtension:
    """Metadata for a loaded extension package."""

    def __init__(
        self,
        *,
        name: str,
        manifest: dict[str, Any] | None = None,
        root_dir: Path | None = None,
        instance: Any = None,
    ) -> None:
        self.name = name
        self.manifest = deepcopy(manifest or {})
        self.root_dir = root_dir
        self.instance = instance
        self.template_dirs: list[str] = []
        self.asset_dirs: list[Path] = []

        if self.root_dir is not None:
            templates_dir = self.root_dir / "templates"
            assets_dir = self.root_dir / "assets"
            if templates_dir.exists():
                self.template_dirs.append(str(templates_dir.resolve()))
            if assets_dir.exists():
                self.asset_dirs.append(assets_dir.resolve())


class ExtensionManager:
    """Loads extension packages and exposes their registries to the build."""

    def __init__(self, config, fs_manager: FileSystemManager) -> None:
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.fs_manager = fs_manager
        self.api = ExtensionAPI()
        self.loaded_extensions: list[LoadedExtension] = []

    @property
    def model_registry(self) -> ContentModelRegistry:
        return self.api.models

    @property
    def frontend_target_registry(self) -> DefinitionRegistry:
        return self.api.frontend_targets

    @property
    def runtime_adapter_registry(self) -> DefinitionRegistry:
        return self.api.runtime_adapters

    @property
    def build_hook_registry(self) -> BuildHookRegistry:
        return self.api.build_hooks

    @property
    def command_registry(self) -> CommandRegistry:
        return self.api.commands

    def detect_and_load_extensions(self) -> list[LoadedExtension]:
        self.api.models.register_many(DEFAULT_MODELS, source="core")

        enabled_extensions = self.config.get("extensions.enabled", [])
        if not isinstance(enabled_extensions, list):
            enabled_extensions = []

        for extension_name in enabled_extensions:
            try:
                loaded_extension = self._load_extension(str(extension_name))
                if loaded_extension is not None:
                    self.loaded_extensions.append(loaded_extension)
            except Exception as exc:
                self.logger.error(
                    "Failed to load extension '%s': %s",
                    extension_name,
                    exc,
                    exc_info=True,
                )

        configured_models = self.config.get("content.models", {})
        if isinstance(configured_models, dict):
            self.api.models.register_many(configured_models, source="config")

        return self.loaded_extensions

    def run_build_hook(self, hook_name: str, **kwargs) -> list[Any]:
        return self.api.build_hooks.run(hook_name, **kwargs)

    def get_template_dirs(self) -> list[str]:
        template_dirs: list[str] = []
        for loaded_extension in self.loaded_extensions:
            template_dirs.extend(loaded_extension.template_dirs)

        deduped: list[str] = []
        for template_dir in template_dirs:
            if template_dir not in deduped:
                deduped.append(template_dir)
        return deduped

    def copy_extension_assets(self, output_dir: Path) -> None:
        for loaded_extension in self.loaded_extensions:
            for asset_dir in loaded_extension.asset_dirs:
                if not asset_dir.exists():
                    continue
                dest_dir = (
                    output_dir
                    / "assets"
                    / "extensions"
                    / slugify(loaded_extension.name)
                )
                self.fs_manager.copy_directory(asset_dir, dest_dir, exist_ok=True)

    def get_context(self) -> dict[str, Any]:
        return {
            "extensions": {
                "enabled": [loaded_extension.name for loaded_extension in self.loaded_extensions],
                "manifests": [deepcopy(loaded_extension.manifest) for loaded_extension in self.loaded_extensions],
            }
        }

    def _load_extension(self, extension_name: str) -> LoadedExtension | None:
        manifest, entrypoint, root_dir = self._resolve_extension(extension_name)
        instance, discovered_root_dir = self._load_entrypoint(entrypoint)
        if root_dir is None:
            root_dir = discovered_root_dir
        loaded_extension = LoadedExtension(
            name=str(manifest.get("name", extension_name)),
            manifest=manifest,
            root_dir=root_dir,
            instance=instance,
        )
        self._register_extension(instance)
        return loaded_extension

    def _resolve_extension(
        self, extension_name: str
    ) -> tuple[dict[str, Any], str, Path | None]:
        entry_point = self._find_entry_point(extension_name)
        if entry_point is not None:
            return (
                {
                    "name": extension_name,
                    "version": 1,
                    "source": "entry_point",
                },
                entry_point.value,
                None,
            )

        manifest_result = self._find_local_manifest(extension_name)
        if manifest_result is not None:
            return manifest_result

        if ":" in extension_name:
            return (
                {"name": extension_name, "version": 1, "source": "direct"},
                extension_name,
                None,
            )

        normalized_name = extension_name.replace("-", "_")
        return (
            {"name": extension_name, "version": 1, "source": "direct"},
            f"extensions.{normalized_name}.extension:get_extension",
            None,
        )

    def _find_entry_point(self, extension_name: str):
        try:
            discovered = metadata.entry_points()
        except Exception:
            return None

        if hasattr(discovered, "select"):
            candidates = discovered.select(group="wg.extensions")
        else:
            candidates = discovered.get("wg.extensions", [])  # pylint: disable=no-member

        for candidate in candidates:
            if candidate.name == extension_name:
                return candidate
        return None

    def _find_local_manifest(
        self, extension_name: str
    ) -> tuple[dict[str, Any], str, Path | None] | None:
        local_paths = self.config.get("extensions.local_paths", ["./extensions"])
        if not isinstance(local_paths, list):
            local_paths = ["./extensions"]

        normalized_name = extension_name.replace("-", "_")
        for raw_base in local_paths:
            base_path = Path(raw_base)
            for candidate_name in [normalized_name, extension_name]:
                candidate_dir = base_path / candidate_name
                manifest_path = candidate_dir / "wg-extension.yaml"
                if not manifest_path.exists():
                    continue

                manifest = yaml.safe_load(self.fs_manager.read_file(manifest_path)) or {}
                if not isinstance(manifest, dict):
                    raise ExtensionLoadError(
                        f"Extension manifest must be a mapping: {manifest_path}"
                    )

                python_cfg = manifest.get("python", {})
                entrypoint = ""
                if isinstance(python_cfg, dict):
                    entrypoint = str(python_cfg.get("entrypoint", "")).strip()
                if not entrypoint:
                    entrypoint = f"extensions.{normalized_name}.extension:get_extension"
                return manifest, entrypoint, candidate_dir.resolve()
        return None

    def _load_entrypoint(self, entrypoint: str) -> tuple[Any, Path | None]:
        module_name, _, attr_name = entrypoint.partition(":")
        attr_name = attr_name or "get_extension"
        module = importlib.import_module(module_name)
        obj = getattr(module, attr_name)
        module_root = Path(module.__file__).resolve().parent if getattr(module, "__file__", None) else None

        if inspect.isclass(obj):
            return obj(), module_root
        if callable(obj):
            return obj(), module_root
        return obj, module_root

    def _register_extension(self, instance: Any) -> None:
        method_map = {
            "register_models": self.api.models,
            "register_frontend_targets": self.api.frontend_targets,
            "register_runtime_adapters": self.api.runtime_adapters,
            "register_build_hooks": self.api.build_hooks,
            "register_cli_commands": self.api.commands,
        }

        for method_name, registry in method_map.items():
            method = getattr(instance, method_name, None)
            if callable(method):
                method(registry)
