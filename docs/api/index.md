# API Reference

This section provides comprehensive reference documentation for all public classes, methods, and functions in the Website Generator codebase.

## Core Modules

### Project Management
- [Project](classes.md#Project) - Main build orchestrator
- [Config](classes.md#Config) - Configuration management
- [Site](classes.md#Site) - In-memory site model
- [Page](classes.md#Page) - Individual page representation

### Managers
- [PluginManager](classes.md#PluginManager) - Plugin discovery and execution
- [ExtensionManager](classes.md#ExtensionManager) - Extension package management
- [ThemeManager](classes.md#ThemeManager) - Theme loading and overrides
- [FrontendManager](classes.md#FrontendManager) - Frontend target builds
- [RuntimeManager](classes.md#RuntimeManager) - Runtime integration

### Engines
- [TemplateEngine](classes.md#TemplateEngine) - Abstract template engine interface
- [DjangoEngine](classes.md#DjangoEngine) - Django template implementation

### Processors
- [ContentProcessor](classes.md#ContentProcessor) - Abstract content processing
- [MarkdownProcessor](classes.md#MarkdownProcessor) - Markdown to HTML conversion

### Plugins
- [BasePlugin](classes.md#BasePlugin) - Plugin base class

### Extensions
- [BaseExtension](classes.md#BaseExtension) - Extension base class

### Utilities
- [FileSystemManager](classes.md#FileSystemManager) - File operations utility

## Usage

All classes are imported from their respective modules:

```python
from core.project import Project
from core.config import Config
# etc.
```

See individual class documentation for method signatures and usage examples.