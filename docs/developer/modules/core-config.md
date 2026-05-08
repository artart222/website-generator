# Core Config Module

## Overview

The `core/config.py` module defines the `Config` class, responsible for loading, validating, and providing access to project configuration settings. It supports both v1 (legacy) and v2 configuration formats, with automatic normalization and deprecation warnings.

The Config class uses YAML files for configuration, provides dotted-notation access to nested settings, and includes comprehensive defaults for all features.

## Architecture

Configuration is loaded from `config.yaml` and merged with defaults. The class provides:
- Dotted access: `config.get("site.name")`
- Attribute access: `config.site['name']`
- Validation with warnings for deprecated features
- Backward compatibility for v1 configs

## Key Classes

### Config

Configuration management class.

#### Attributes

- `settings: dict[str, Any]` - Merged configuration dictionary
- `warnings: list[str]` - Deprecation and validation warnings
- `fs_manager: FileSystemManager` - File system operations

#### Key Methods

- `__init__(fs_manager: FileSystemManager = None)` - Initializes with defaults
- `load(filepath: str)` - Loads and merges YAML config
- `get(key: str, default: Any = None) -> Any` - Dotted-notation access
- `validate()` - Validates config and collects warnings
- `_apply_compat_aliases()` - Normalizes v1 to v2 format

## Configuration Structure

Supports nested sections:
- `site`: Site metadata and navigation
- `content`: Collections, models, source directories
- `theme`: Theme settings and overrides
- `build`: Output, templates, engines
- `extensions`: Extension packages
- `frontend`: Frontend targets
- `runtime`: Runtime integration
- `plugins`: Plugin configuration
- `experimental`: React, Tailwind, data export

## Validation

Validates:
- Version (1 or 2)
- Template engine (only 'django' supported)
- Runtime target types
- Required fields presence

## Usage Examples

```python
from core.config import Config

config = Config()
config.load('config.yaml')
config.validate()

site_name = config.get('site.name')
# or
site_name = config.site['name']
```

## Dependencies

- `utils.fs_manager`: File operations
- External: yaml, copy, pathlib, logging

## Error Handling

- Raises ValueError for invalid versions or unsupported engines
- Collects warnings for deprecated features
- Logs configuration loading

## Extensibility

Configuration can be extended by extensions to add custom sections and settings.