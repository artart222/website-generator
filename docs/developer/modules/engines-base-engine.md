# Engines Base Engine Module

## Overview

The `engines/base_engine.py` module defines the `TemplateEngine` abstract base class, which provides the interface for template rendering engines. It allows different template engines (Django, Jinja2, etc.) to be used interchangeably.

The base class defines the contract that all template engines must implement.

## Architecture

Template engines implement the abstract methods to:
- Render templates by name
- Render template strings
- Load templates from the filesystem

## Key Classes

### TemplateEngine

Abstract base class for template engines.

#### Abstract Methods

- `render(template_name: str, context: dict) -> str` - Renders named template with context
- `render_from_string(template_string: str, context: dict) -> str` - Renders string template
- `load_template(template_name: str) -> Template | str` - Loads template by name

## Implementation

Concrete implementations:
- `DjangoEngine` in `django_engine.py`
- Factory function in `factory.py` creates engines by name

## Usage Examples

```python
from engines.base_engine import TemplateEngine

class MyEngine(TemplateEngine):
    def render(self, template_name, context):
        # implementation
        pass
```

## Dependencies

- External: abc (for ABC)

## Error Handling

Abstract methods raise NotImplementedError if not overridden.

## Extensibility

New template engines can be added by implementing the TemplateEngine interface.