# Website Generator Architecture (v1)

## 1. Overview

This document outlines the proposed software architecture for a static website generator. The architecture is designed using Object-Oriented Principles (OOP) to promote modularity, testability, extensibility, and ease of maintenance. The core goal is to separate concerns, allowing developers to work on different parts of the system independently and to facilitate long-term development and feature additions.

## 2. Guiding Principles

* **Modularity:** Components should be self-contained with well-defined responsibilities.
* **Extensibility:** The system should be easy to extend with new features, content types, or plugins without requiring major core changes.
* **Separation of Concerns:** Data representation, logic, rendering, and I/O operations should be handled by distinct components.
* **Testability:** Individual components should be easily testable in isolation.
* **Clarity:** The architecture should be understandable to new developers.

## 3. Core Components & Classes

The system will be built around the following core classes:

### 3.1. Project & Configuration

* **`Project`**
    * **Responsibility:** Represents the entire website generation project. Manages global settings, source and output paths, and orchestrates the build process.
    * **Attributes:**
        * `config: Configuration` - Holds all project settings.
        * `site: Site` - The main site object to be built.
        * `plugin_manager: PluginManager` - Manages active plugins.
        * `fs_manager
        * : FileSystemManager` - Utility for file operations.
        * `template_engine_instance: TemplateEngine` - The chosen template engine.
    * **Methods:**
        * `__init__(config_path: str)`: Initializes the project by loading configuration.
        * `load_plugins()`: Discovers and loads configured plugins.
        * `initialize_site()`: Creates and populates the `Site` object based on source files and config.
        * `build()`: Orchestrates the entire site generation process (e.g., pre-build hooks, page rendering, asset copying, post-build hooks).
        * `get_template_engine() -> TemplateEngine`: Returns the configured template engine.

* **`Configuration`**
    * **Responsibility:** Loads, stores, and provides access to project settings from a configuration file (e.g., YAML, JSON, TOML).
    * **Attributes:**
        * `settings: dict` - Internal dictionary holding all configuration data.
        * `source_directory: str` - Path to content and template sources.
        * `output_directory: str` - Path where the generated site will be saved.
        * `templates_directory: str` - Path to template files within the source directory.
        * `assets_directory: str` - Path to static assets within the source directory.
        * `pages_directory: str` - Path to page content files.
        * `default_template: str` - Default template to use if a page doesn't specify one.
        * `plugins: list[dict]` - Configuration for plugins to be loaded.
    * **Methods:**
        * `load(filepath: str)`: Loads configuration from the given file.
        * `get(key: str, default: Any = None) -> Any`: Retrieves a setting.
        * `set(key: str, value: Any)`: Sets a setting (primarily for internal/plugin use).

### 3.2. Site Structure & Content

* **`Site`**
    * **Responsibility:** Represents the website to be generated. Contains all pages, assets, and site-wide metadata.
    * **Attributes:**
        * `name: str` - Name of the site.
        * `base_url: str` - Base URL for the site (used for absolute links).
        * `pages: list[Page]` - Collection of all pages in the site.
        * `assets: list[Asset]` - Collection of all static assets.
        * `global_data: dict` - Data accessible to all pages and templates (e.g., site navigation).
        * `config: Configuration` - Reference to the project configuration.
    * **Methods:**
        * `add_page(page: Page)`
        * `add_asset(asset: Asset)`
        * `discover_content(source_dir: str, pages_dir_name: str)`: Scans content directories to create `Page` objects.
        * `discover_assets(source_dir: str, assets_dir_name: str)`: Scans asset directories to create `Asset` objects.
        * `get_page_by_slug(slug: str) -> Page | None`

* **`Page`**
    * **Responsibility:** Represents a single page in the website.
    * **Attributes:**
        * `title: str`
        * `slug: str` - URL-friendly identifier (e.g., "about-us").
        * `source_filepath: str` - Path to the original content file (e.g., Markdown).
        * `output_filepath: str` - Calculated path for the generated HTML file.
        * `template_name: str | None` - Name of the template to use for rendering this page.
        * `metadata: dict` - Frontmatter or other page-specific data.
        * `raw_content: str` - The raw content read from the source file.
        * `processed_content: str` - Content after processing (e.g., Markdown to HTML).
        * `sections: list[Section]` - (Optional) If page structure is more complex than just main content.
        * `elements: list[Element]` - (Alternative to sections) A flat list of elements if sections are not used.
        * `parent_site: Site` - Reference to the parent site.
    * **Methods:**
        * `__init__(source_filepath: str, config: Configuration, parent_site: Site)`
        * `load_content_and_metadata()`: Reads the source file, parses frontmatter/metadata.
        * `process_content(content_processor: ContentProcessor | None)`: Converts raw content (e.g., Markdown to HTML).
        * `render(template_engine: TemplateEngine, global_data: dict) -> str`: Renders the page to an HTML string.
        * `get_context() -> dict`: Prepares the data context for template rendering.
        * `calculate_output_path(output_dir: str)`

* **`Section`** (Optional, for complex page layouts)
    * **Responsibility:** Represents a logical, reusable part of a page (e.g., header, footer, sidebar, content block).
    * **Attributes:**
        * `name: str` - Identifier for the section.
        * `template_name: str | None` - Template specific to this section.
        * `elements: list[Element]` - Content elements within this section.
        * `data: dict` - Data specific to this section.
    * **Methods:**
        * `add_element(element: Element)`
        * `render(template_engine: TemplateEngine, page_context: dict, global_data: dict) -> str`

* **`Element` (Abstract Base Class)**
    * **Responsibility:** Base class for all content elements (e.g., paragraph, heading, image).
    * **Attributes:**
        * `element_type: str` - e.g., 'paragraph', 'image'.
        * `attributes: dict` - HTML attributes (e.g., `{'class': 'foo', 'id': 'bar'}`).
    * **Methods:**
        * `render(template_engine: TemplateEngine, context: dict) -> str` (Abstract method to be implemented by subclasses).

* **Concrete `Element` Subclasses:**
    * `TextElement(Element)`: `text_content: str`
    * `ImageElement(Element)`: `src: str`, `alt: str`
    * `ListElement(Element)`: `items: list[str | Element]`, `ordered: bool`
    * `CustomHTMLElement(Element)`: `html_string: str`
    * *(More can be added as needed, e.g., `VideoElement`, `TableElement`)*

* **`Asset`**
    * **Responsibility:** Represents a static file (CSS, JS, image, font) to be copied to the output directory.
    * **Attributes:**
        * `source_filepath: str`
        * `output_subpath: str` - Relative path within the output assets directory.
    * **Methods:**
        * `get_output_path(base_output_dir: str, assets_output_subdir: str) -> str`

### 3.3. Processing & Rendering

* **`TemplateEngine` (Abstract Base Class / Interface)**
    * **Responsibility:** Defines the interface for template rendering.
    * **Methods:**
        * `render(template_name: str, context: dict) -> str` (Abstract)
        * `render_string(template_string: str, context: dict) -> str` (Abstract)
        * `load_template(template_name: str)` (Abstract, or handled internally)

* **Concrete `TemplateEngine` Implementations:**
    * `Jinja2TemplateEngine(TemplateEngine)`: Uses Jinja2.
    * `LiquidTemplateEngine(TemplateEngine)`: Uses Liquid.
    * *(Others can be added)*

* **`ContentProcessor` (Abstract Base Class / Interface)**
    * **Responsibility:** Defines an interface for processing raw page content (e.g., Markdown to HTML).
    * **Methods:**
        * `process(raw_content: str) -> str` (Abstract)

* **Concrete `ContentProcessor` Implementations:**
    * `MarkdownProcessor(ContentProcessor)`: Converts Markdown to HTML.
    * `PlainTextProcessor(ContentProcessor)`: Passes through text as is (or basic formatting).

### 3.4. Extensibility

* **`PluginManager`**
    * **Responsibility:** Manages the lifecycle of plugins.
    * **Attributes:**
        * `plugins: list[Plugin]`
        * `project_ref: Project` - Reference to the main project instance for context.
    * **Methods:**
        * `load_plugins(plugin_configs: list[dict])`: Loads plugins based on configuration.
        * `register_plugin(plugin: Plugin)`
        * `trigger_hook(hook_name: str, *args, **kwargs)`: Calls the corresponding method on all registered plugins that implement the hook.

* **`Plugin` (Abstract Base Class / Interface)**
    * **Responsibility:** Defines the interface for plugins. Plugins can hook into various stages of the build process.
    * **Attributes:**
        * `name: str`
    * **Methods (Examples of Hooks):**
        * `setup(project: Project)`: Called when the plugin is loaded, receives project instance.
        * `on_config_loaded(config: Configuration)`
        * `on_before_build(site: Site)`
        * `on_before_page_render(page: Page, context: dict)`
        * `on_after_page_render(page: Page, html_content: str) -> str`: Can modify HTML content.
        * `on_after_build(site: Site, output_directory: str)`
        * *(More hooks can be defined as needed, e.g., for new element types, new template functions)*

### 3.5. Utilities

* **`FileSystemManager`**
    * **Responsibility:** Provides a consistent API for file system operations, aiding in testability (can be mocked).
    * **Methods:**
        * `read_file(filepath: str) -> str`
        * `write_file(filepath: str, content: str)`
        * `copy_file(source_path: str, dest_path: str)`
        * `copy_directory(source_dir: str, dest_dir: str, exist_ok: bool = False)`
        * `create_directory(dir_path: str, exist_ok: bool = True)`
        * `list_files(directory: str, recursive: bool = False, extensions: list[str] | None = None) -> list[str]`
        * `path_exists(path: str) -> bool`
* **`logging_setup`** Module
    * **Responsibility:** To provide a configurable logging setup for the entire application, allowing the log level to be set based on the project's configuration.

## 4. Workflow / Data Flow

1.  **Initialization:**
    * `Project` is instantiated with a config file path.
    * `Configuration` loads settings.
    * `PluginManager` loads and initializes configured `Plugin`s. Plugins register their hooks.
    * `TemplateEngine` instance is created based on config.
    * `FileSystemManager` is available.

2.  **Site Population (within `Project.initialize_site()`):**
    * `Site` object is created.
    * `Plugin Hook`: `on_config_loaded`.
    * `Site.discover_content()`: Scans content directories. For each content file:
        * `Page` object is created.
        * `Page.load_content_and_metadata()` parses frontmatter and raw content.
        * `Page.process_content()` uses a `ContentProcessor` (e.g., `MarkdownProcessor`) to convert raw content.
        * Page is added to `Site.pages`.
    * `Site.discover_assets()`: Scans asset directories, creates `Asset` objects, adds to `Site.assets`.

3.  **Build Process (within `Project.build()`):**
    * `Plugin Hook`: `on_before_build`.
    * **Page Rendering Loop:** For each `Page` in `Site.pages`:
        * `Plugin Hook`: `on_before_page_render`.
        * `Page.calculate_output_path()`.
        * `context = Page.get_context()` (merges page data, site global data).
        * `html_content = Page.render(template_engine, context)`.
        * `Plugin Hook`: `on_after_page_render` (can modify `html_content`).
        * `FileSystemManager.write_file(page.output_filepath, html_content)`.
    * **Asset Copying Loop:** For each `Asset` in `Site.assets`:
        * `FileSystemManager.copy_file(asset.source_filepath, asset.get_output_path(...))`.
    * `Plugin Hook`: `on_after_build`.

## 5. Directory Structure (Example)

This section shows an example directory structure for a **user's project** and for the **generator's own source code**. The user project structure is inspired by conventions from popular static site generators, using top-level folders for different content types.

**User Project Structure (`my-website-project/`)**

my-website-project/
├── _config.yaml                  # Project configuration.
├── _posts/                       # Blog posts (e.g., YYYY-MM-DD-my-post-title.md)
│   └── 2025-06-06-hello-world.md
├── _pages/                       # Other pages like 'About' or 'Contact'.
│   ├── about.md
│   └── contact.md
├── _layouts/                     # Base templates that content is injected into.
│   ├── default.html
│   └── post.html
├── _includes/                    # Reusable template partials (e.g., header, footer).
│   ├── header.html
│   └── footer.html
├── _data/                        # Global data files (e.g., navigation.yml).
│   └── navigation.yml
├── assets/                       # Static files that will be copied over.
│   ├── css/
│   │   └── main.css
│   ├── js/
│   │   └── app.js
│   └── images/
│       └── logo.svg
├── _plugins/                     # Custom local plugins for this specific project.
│   └── my_custom_filter.py
└── _site/                        # Generated website output (ignored by VCS).


**Generator's Source Code Structure (`website_generator_program/`)**

website_generator_program/
├── __init__.py
├── main.py                       # CLI entry point.
├── core/
│   ├── init.py
│   ├── project.py
│   ├── site.py
│   ├── config.py
│   └── page.py
├── processors/
│   ├── init.py
│   ├── base_processor.py         # Contains ContentProcessor ABC.
│   └── markdown_processor.py
|   └── factory.py
├── engines/
│   ├── __init__.py
│   ├── base_engine.py            # Contains TemplateEngine ABC.
│   ├── django_engine.py
|   └── factory.py
├── plugins/
│   ├── __init__.py
│   ├── base_plugin.py            # Plugin ABC and PluginManager.
│   └── sitemap_plugin.py         # Example built-in plugin.
└── utils/
    ├── init.py
    |── fs_manager.py
    └── logging_setup.py


## 6. Future Considerations & Extensibility Points

* **Content Sources:** Abstract content loading to support databases, headless CMS, APIs.
* **Theming:** Develop a more formal theming system.
* **Internationalization (i18n):** Plan for multi-language support.
* **Incremental Builds:** Only rebuild changed content for faster development.
* **Server Mode:** Built-in development server with live reloading.
* **Advanced Element Types:** Components that can fetch their own data or have complex rendering logic.
* **Data Pipelines:** Allow processing and transformation of data before it's used in templates.

This architecture provides a solid foundation for building a flexible and powerful website generator. Each component has clear responsibilities, promoting separation of concerns and making the system easier to develop, test, and extend over time.