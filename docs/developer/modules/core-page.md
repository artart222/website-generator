# Core Page Module

## Overview

The `core/page.py` module defines the `Page` class, which represents individual content documents in the website. It handles loading source files, processing content and metadata, and storing page attributes used for rendering and routing.

The Page class encapsulates all data for a single page, from source file to rendered output, including frontmatter metadata, processed content, and routing information.

## Architecture

Page instances are created during content discovery and populated through:
- `read_source_file()` - Loads raw content
- `process_content()` - Converts Markdown to HTML
- `process_metadata()` - Extracts YAML frontmatter
- `_populate_attributes()` - Maps metadata to attributes

## Key Classes

### Page

Represents a source document or generated page.

#### Attributes

- `source_filepath: Path` - Path to source file
- `raw_content: str` - Raw file content
- `processed_content: str` - Processed HTML content
- `metadata: dict[str, Any]` - Frontmatter data
- `title: str` - Page title
- `slug: str` - URL slug
- `page_type: str | None` - Content type
- `summary/description: str` - Page descriptions
- `author/keywords/tags/categories: list[str]` - Metadata lists
- `date: str` - Publication date
- `draft: bool` - Draft status
- `image: str` - Featured image
- `collection: str | None` - Collection name
- `layout: str | None` - Template layout
- `blocks/islands: list[dict[str, Any]]` - Page blocks
- `output_path: Path | None` - Generated file path
- `abs_url/root_rel_url: str` - URLs

#### Key Methods

- `__init__(source_filepath, config, fs_manager)` - Initializes page
- `load(content_processor)` - Loads and processes content
- `read_source_file()` - Reads source file
- `process_content(content_processor)` - Processes content
- `process_metadata(content_processor)` - Extracts metadata
- `_populate_attributes()` - Maps metadata to attributes

## Content Processing

Supports content processors for different file types (Markdown, etc.) that extract frontmatter and convert content.

## Usage Examples

```python
from core.page import Page
from core.config import Config

config = Config()
page = Page('source/index.md', config, fs_manager)
page.load(content_processor)
print(page.title)
```

## Dependencies

- `processor.base_processor`: Content processing interface
- `utils.fs_manager`: File operations
- `core.config`: Configuration
- External: pathlib, slugify, logging

## Error Handling

- Handles missing source files gracefully
- Validates metadata structure
- Logs loading operations

## Extensibility

Page attributes can be extended by plugins and content models to add custom fields.