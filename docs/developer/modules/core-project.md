# Core Project Module

## Overview

The `core/project.py` module defines the `Project` class, the central orchestrator for the website generation build process. It initializes and coordinates all subsystem managers (theme, plugin, extension, frontend, runtime), manages the build lifecycle with hooks, and handles the end-to-end site generation from configuration to output.

The Project class follows a factory pattern for template engines and processors, uses a hook system for extensibility, and ensures proper sequencing of build phases.

## Architecture

The Project acts as the composition root, assembling:
- Configuration management
- Site content discovery and modeling
- Template rendering
- Asset processing
- Plugin and extension execution
- Frontend target building
- Runtime integration

## Key Classes

### Project

Main build orchestrator class.

#### Attributes

- `config: Config` - Project configuration object
- `site: Site` - In-memory site model
- `router: Router` - URL routing logic
- `theme_manager: ThemeManager` - Theme loading and overrides
- `plugin_manager: PluginManager` - Plugin discovery and execution
- `extension_manager: ExtensionManager` - Extension package management
- `frontend_manager: FrontendManager` - Frontend target builds
- `runtime_manager: RuntimeManager` - Runtime integration
- `template_engine: TemplateEngine` - Configured template engine instance
- `fs_manager: FileSystemManager` - File system operations utility

#### Key Methods

- `__init__(config: Config)` - Initializes all managers and sets up template engine
- `build()` - Executes the complete build pipeline with hook execution
- `_discover_and_load_pages()` - Scans source directories for content files
- `_apply_content_models()` - Validates and applies content schemas
- `_assign_routes()` - Generates output paths and URLs
- `_render_pages()` - Renders all pages to HTML
- `_export_json_data()` - Exports page data as JSON
- `_copy_assets()` - Copies static assets to output
- `_build_tailwind()` - Builds Tailwind CSS if configured

## Build Lifecycle

The `build()` method orchestrates these phases:

1. Pre-build hooks (extensions and plugins)
2. Output directory preparation
3. Runtime catalog snapshot fetching
4. Page discovery and content processing
5. Content model application
6. Site data loading
7. Route assignment
8. Page rendering
9. JSON export
10. Frontend target building
11. Runtime manifest emission
12. Tailwind CSS building
13. Asset copying
14. Post-build hooks

## Usage Examples

```python
from core.config import Config
from core.project import Project

# Load configuration
config = Config()
config.load('config.yaml')

# Create and build project
project = Project(config)
project.build()
```

## Dependencies

- `engines.factory`: Template engine creation
- `processor.factory`: Content processor creation
- `utils.fs_manager`: File operations
- Core modules: config, site, router, theme_manager, etc.
- External: yaml, slugify, pathlib

## Error Handling

- Validates output directory is not project root
- Handles runtime catalog snapshot failures gracefully
- Logs build progress and errors

## Extensibility

Supports extension through:
- Plugin hooks at lifecycle points
- Extension build hooks
- Custom template engines via factory
- Content processors via factory