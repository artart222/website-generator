# Core Extension Manager Module

## Overview

The `core/extension_manager.py` module defines the `ExtensionManager` class, which handles loading and managing extension packages. Extensions are installable packages that provide content models, frontend targets, runtime adapters, build hooks, and CLI commands.

The extension system allows third-party packages to extend the generator's functionality without modifying core code.

## Architecture

Extension loading:
1. Discovers extensions from config and installed packages
2. Loads extension manifests
3. Instantiates extension classes
4. Calls registration hooks to populate registries

Provides registries for models, hooks, targets, etc.

## Key Classes

### ExtensionManager

Manages extension package loading and registries.

#### Attributes

- `config: Config` - Project configuration
- `fs_manager: FileSystemManager` - File operations
- `extensions: list[LoadedExtension]` - Loaded extensions
- `api: ExtensionAPI` - Extension registries

#### Key Methods

- `__init__(config, fs_manager)` - Initializes manager
- `detect_and_load_extensions()` - Loads extensions from config
- `run_build_hook(hook_name, **kwargs)` - Executes build hooks

### ExtensionAPI

Mutable registries for extensions.

#### Attributes

- `models: ContentModelRegistry` - Content model definitions
- `frontend_targets: DefinitionRegistry` - Frontend build targets
- `runtime_adapters: DefinitionRegistry` - Runtime integration adapters
- `build_hooks: BuildHookRegistry` - Build lifecycle hooks
- `commands: CommandRegistry` - CLI commands

### LoadedExtension

Metadata for loaded extension.

#### Attributes

- `name: str` - Extension name
- `manifest: dict[str, Any]` - Extension manifest
- `root_dir: Path | None` - Extension directory
- `instance: Any` - Extension instance

## Extension Discovery

Loads extensions from:
- `extensions.enabled` config list (installed packages)
- `extensions.local_paths` directories (local extensions)

## Registration Hooks

Extensions implement methods:
- `register_models(api)` - Add content models
- `register_frontend_targets(api)` - Add frontend targets
- `register_runtime_adapters(api)` - Add runtime adapters
- `register_build_hooks(api)` - Add build hooks
- `register_cli_commands(api)` - Add CLI commands

## Usage Examples

```python
from core.extension_manager import ExtensionManager

manager = ExtensionManager(config, fs_manager)
manager.detect_and_load_extensions()
models = manager.api.models
```

## Dependencies

- `core.config`: Configuration
- `core.content_models`: Model registry
- `utils.fs_manager`: File operations
- External: importlib, inspect, yaml, pathlib, logging

## Error Handling

- Raises `ExtensionLoadError` for load failures
- Logs loading issues
- Continues with available extensions

## Extensibility

Extensions can register custom models, hooks, and integrations to extend the generator.