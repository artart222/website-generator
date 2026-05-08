# Core Plugin Manager Module

## Overview

The `core/plugin_manager.py` module defines the `PluginManager` class, responsible for discovering, loading, and executing plugins during the build process. It implements a hook system that allows plugins to inject behavior at various lifecycle points.

Plugins are Python classes in the `plugins/` directory that inherit from `BasePlugin` and are enabled in the config.

## Architecture

Plugin discovery:
1. Scans `plugins/` directory for Python files
2. Imports modules dynamically
3. Finds classes inheriting from `BasePlugin`
4. Instantiates enabled plugins from config

Hook execution runs methods on all loaded plugins if they exist.

## Key Classes

### PluginManager

Manages plugin discovery, loading, and hook execution.

#### Attributes

- `config: Config` - Project configuration
- `site: Site` - Site instance
- `plugins: list[BasePlugin]` - Loaded plugin instances

#### Key Methods

- `__init__(config, site)` - Initializes manager
- `detect_and_load_plugins()` - Discovers and loads plugins from config
- `run_hook(hook_name, *args, **kwargs)` - Executes hook on all plugins

## Plugin Discovery

Scans `plugins/` directory, imports modules, finds `BasePlugin` subclasses, and instantiates those listed in `config.plugins`.

## Hook System

Hooks are method names called on plugins at build lifecycle points:
- `after_config_loaded`
- `before_build`
- `after_pages_discovered`
- `after_collections_loaded`
- `after_routes_built`
- `after_build`

## Usage Examples

```python
from core.plugin_manager import PluginManager

manager = PluginManager(config, site)
plugins = manager.detect_and_load_plugins()
manager.run_hook('before_build', site=site, config=config)
```

## Dependencies

- `core.config`: Configuration access
- `core.site`: Site instance
- `plugins.base_plugin`: Base plugin class
- External: importlib, inspect, pathlib, logging

## Error Handling

- Logs import failures
- Warns about missing plugins
- Continues execution with available plugins

## Extensibility

Plugins can define any hook methods to extend build behavior without modifying core code.