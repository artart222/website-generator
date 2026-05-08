# Core Site Module

## Overview

The `core/site.py` module defines the `Site` class, which represents the in-memory model of the entire website during the build process. It holds all pages, site-wide metadata, navigation configuration, and provides methods for querying and manipulating site content.

The Site class acts as the central data structure that plugins, extensions, and the build process operate on, maintaining the website's structure and relationships.

## Architecture

The Site class is initialized with configuration and populated during the build process:
- Pages are added via `add_page()`
- Site data is set via `set_data()`
- Navigation is built from config via `build_navigation()`

It provides query methods for finding pages by URL, type, or collection.

## Key Classes

### Site

In-memory site model.

#### Attributes

- `config: Config` - Project configuration reference
- `name: str` - Site name from config
- `base_url: str` - Base URL for the site
- `pages: list[Page]` - All pages in the site
- `data: dict[str, Any]` - Site-wide data accessible to templates
- `navigation_items: list[dict[str, Any]]` - Processed navigation items
- `header: str` - HTML header string for navigation

#### Key Methods

- `__init__(config: Config)` - Initializes site with config values
- `add_page(page: Page)` - Adds a page to the site
- `set_data(data: dict[str, Any])` - Sets site-wide data
- `get_pages() -> list[Page]` - Returns all pages
- `get_page_by_url(url: str) -> Page | None` - Finds page by absolute URL
- `get_page_by_type(page_type: str) -> list[Page]` - Finds pages by type
- `get_collection_index_page(collection_name: str) -> Page | None` - Finds collection index page
- `build_navigation() -> list[dict[str, Any]]` - Builds navigation from config

## Navigation Building

The `build_navigation()` method processes the `site.navigation` config array, resolving URLs from:
- Direct `url` values
- `collection_index` references
- `type` page type lookups
- `collection` index lookups

Generates HTML header and navigation items with external link detection.

## Usage Examples

```python
from core.config import Config
from core.site import Site

config = Config()
site = Site(config)
site.add_page(page_instance)
navigation = site.build_navigation()
```

## Dependencies

- `core.config`: Configuration access
- `core.page`: Page class
- External: slugify, logging

## Error Handling

- Validates navigation config structure
- Gracefully handles missing or invalid navigation items
- Logs page additions

## Extensibility

Site data can be extended by plugins and extensions to add custom metadata accessible in templates.