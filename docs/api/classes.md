# API Classes Reference

## Project

Main build orchestrator class.

### Constructor
```python
Project(config: Config)
```

### Methods

#### build() -> None
Executes the complete build pipeline.

**Lifecycle phases:**
1. Pre-build hooks
2. Output directory preparation
3. Runtime catalog snapshot
4. Page discovery and processing
5. Content model application
6. Site data loading
7. Route assignment
8. Page rendering
9. JSON export
10. Frontend target building
11. Runtime manifest emission
12. Tailwind building
13. Asset copying
14. Post-build hooks

#### _discover_and_load_pages() -> None
Scans source directories for content files and creates Page instances.

#### _apply_content_models(only_missing: bool = False) -> None
Validates and applies content schemas to pages.

#### _assign_routes() -> None
Generates output paths and URLs for all pages.

#### _render_pages() -> None
Renders all pages to HTML using templates.

#### _export_json_data() -> None
Exports page data as JSON files.

#### _copy_assets() -> None
Copies static assets to output directory.

### Attributes
- `config: Config` - Project configuration
- `site: Site` - Site model
- `template_engine: TemplateEngine` - Active template engine

---

## Config

Configuration management class.

### Constructor
```python
Config(fs_manager: FileSystemManager = None)
```

### Methods

#### load(filepath: str) -> None
Loads YAML configuration from file.

#### get(key: str, default: Any = None) -> Any
Retrieves configuration value using dotted notation.

**Examples:**
```python
config.get('site.name')
config.get('build.output_directory', './output')
```

#### validate() -> None
Validates configuration and collects warnings.

**Raises:**
- `ValueError` for invalid versions or unsupported engines

### Attributes
- `settings: dict[str, Any]` - Configuration dictionary
- `warnings: list[str]` - Validation warnings

---

## Site

In-memory site model.

### Constructor
```python
Site(config: Config)
```

### Methods

#### add_page(page: Page) -> None
Adds a page to the site.

#### get_pages() -> list[Page]
Returns all pages.

#### get_page_by_url(url: str) -> Page | None
Finds page by absolute URL.

#### build_navigation() -> list[dict[str, Any]]
Builds navigation from config.

### Attributes
- `pages: list[Page]` - All pages
- `data: dict[str, Any]` - Site-wide data
- `navigation_items: list[dict[str, Any]]` - Navigation structure

---

## Page

Individual page representation.

### Constructor
```python
Page(source_filepath: str, config: Config, fs_manager: FileSystemManager = None)
```

### Methods

#### load(content_processor: ContentProcessor = None) -> None
Loads and processes page content.

#### process_content(content_processor: ContentProcessor) -> None
Converts raw content to processed format.

#### process_metadata(content_processor: ContentProcessor) -> None
Extracts metadata from frontmatter.

### Attributes
- `title: str` - Page title
- `slug: str` - URL slug
- `processed_content: str` - Rendered content
- `metadata: dict[str, Any]` - Frontmatter data
- `abs_url: str` - Absolute URL
- `output_path: Path` - Output file path

---

## PluginManager

Plugin discovery and execution.

### Constructor
```python
PluginManager(config: Config, site: Site)
```

### Methods

#### detect_and_load_plugins() -> list[BasePlugin]
Discovers and loads plugins from config.

#### run_hook(hook_name: str, **kwargs) -> None
Executes hook method on all plugins.

### Attributes
- `plugins: list[BasePlugin]` - Loaded plugins

---

## ExtensionManager

Extension package management.

### Constructor
```python
ExtensionManager(config: Config, fs_manager: FileSystemManager)
```

### Methods

#### detect_and_load_extensions() -> None
Loads extension packages.

#### run_build_hook(hook_name: str, **kwargs) -> list[Any]
Executes build hooks from extensions.

### Attributes
- `extensions: list[LoadedExtension]` - Loaded extensions
- `api: ExtensionAPI` - Extension registries

---

## TemplateEngine

Abstract template engine interface.

### Abstract Methods

#### render(template_name: str, context: dict) -> str
Renders named template.

#### render_from_string(template_string: str, context: dict) -> str
Renders template string.

#### load_template(template_name: str) -> Template | str
Loads template by name.

---

## BasePlugin

Plugin base class.

### Methods

#### __init__() -> None
Initializes plugin.

### Decorators

#### @log_hook
Automatically logs hook execution.

---

## ContentProcessor

Abstract content processing interface.

### Abstract Methods

#### process(content: str) -> str
Processes content.

#### get_metadata() -> dict[str, Any]
Extracts metadata.

---

## FileSystemManager

File operations utility.

### Methods

#### read_file(path: Path) -> str
Reads file content.

#### write_file(path: Path, content: str) -> None
Writes content to file.

#### create_directory(path: Path) -> None
Creates directory.

#### copy_file(src: Path, dst: Path) -> None
Copies file.