# Core Config Module

## Overview

The `core/config.py` module defines the `Config` class, responsible for loading, validating, and providing access to project configuration settings. It uses a single nested v2 schema validated through `core/config_schema.py`.

The Config class uses YAML files for configuration, provides dotted-notation access to nested settings, and includes comprehensive defaults for all features.

## Architecture

Configuration is loaded from `config.yaml` and merged with defaults. The class provides:

- Dotted access: `config.get("site.name")`
- Typed schema: `config.schema` (`AppConfig` dataclass tree)
- Fail-loud loading: missing files and invalid YAML raise `ConfigError`

## Key Classes

### Config

Configuration management class.

#### Attributes

- `settings: dict[str, Any]` - Nested configuration dictionary (single source of truth)
- `schema: AppConfig` - Typed, frozen view of settings
- `fs_manager: FileSystemPort` - File system operations

#### Key Methods

- `__init__(fs_manager: FileSystemPort | None = None)` - Initializes with defaults
- `load(filepath: str)` - Loads and validates YAML config
- `get(key: str, default: Any = None) -> Any` - Dotted-notation access

## Configuration Structure

Nested v2 sections:

- `site`: Site metadata and navigation
- `content`: Collections, models, source directories
- `theme`: Theme settings and overrides
- `build`: Output, templates, engines, `strict`, `incremental`
- `extensions`: Extension packages
- `frontend`: Frontend targets
- `runtime`: Runtime integration
- `integrations`: Payment/notification/shipping providers
- `plugins`: Plugin configuration
- `experimental`: React, Tailwind, data export

## Validation

- Root `version` should be `2`
- Invalid YAML or missing config file raises `ConfigError`
- `build.strict` defaults to `true` (use CLI `--lenient` to relax plugin/runtime errors)

## Usage Examples

```python
from core.config import Config

config = Config()
config.load("config.yaml")
print(config.get("site.name"))
print(config.schema.build.output_directory)
```
