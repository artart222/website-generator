# Writing Custom Plugins

This tutorial shows how to create custom plugins for the Website Generator.

## Plugin Basics

Plugins are Python classes that inherit from `BasePlugin` and are placed in the `plugins/` directory. They can hook into the build lifecycle to modify behavior.

## Step 1: Create Plugin File

Create `plugins/my_plugin.py`:

```python
from plugins.base_plugin import BasePlugin

class MyPlugin(BasePlugin):
    """My custom plugin example."""

    def __init__(self):
        super().__init__()

    # Hook methods
    def after_config_loaded(self, site, config, fs_manager, extension_manager):
        """Called after configuration is loaded."""
        print("Config loaded!")

    def before_build(self, site, config, fs_manager):
        """Called before build starts."""
        print("Starting build...")

    def after_pages_discovered(self, site, config, fs_manager):
        """Called after pages are discovered."""
        print(f"Found {len(site.pages)} pages")

    def after_build(self, site, config, fs_manager):
        """Called after build completes."""
        print("Build complete!")
```

## Step 2: Enable Plugin

Add to `config.yaml`:

```yaml
plugins:
  - MyPlugin
```

## Step 3: Test Plugin

```bash
wg build
```

You should see the print statements in the logs.

## Common Hook Examples

### Adding Custom Data

```python
def after_collections_loaded(self, site, config, fs_manager):
    """Add custom data to site."""
    site.data['custom_var'] = 'Hello from plugin'
```

Access in templates: `{{ site.data.custom_var }}`

### Modifying Pages

```python
def after_pages_discovered(self, site, config, fs_manager):
    """Modify page metadata."""
    for page in site.pages:
        if 'custom' in page.tags:
            page.metadata['special'] = True
```

### Generating Extra Files

```python
def after_build(self, site, config, fs_manager):
    """Generate additional output files."""
    output_dir = Path(config.get('build.output_directory'))
    extra_file = output_dir / 'extra.json'

    data = {'generated': True, 'pages': len(site.pages)}
    fs_manager.write_file(extra_file, json.dumps(data))
```

### Custom Content Processing

```python
def after_pages_modeled(self, project, site, config):
    """Custom processing after modeling."""
    for page in site.pages:
        # Custom logic here
        pass
```

## Plugin with Configuration

```python
class ConfigurablePlugin(BasePlugin):
    """Plugin that reads config."""

    def after_config_loaded(self, site, config, fs_manager, extension_manager):
        self.my_setting = config.get('plugins.my_plugin.setting', 'default')

    def before_build(self, site, config, fs_manager):
        print(f"My setting: {self.my_setting}")
```

Config:
```yaml
plugins:
  - ConfigurablePlugin

plugins.my_plugin.setting: custom_value
```

## Error Handling

```python
def after_pages_discovered(self, site, config, fs_manager):
    try:
        # Risky operation
        pass
    except Exception as e:
        self.logger.error(f"Plugin error: {e}")
```

## Best Practices

1. Use descriptive class names
2. Document hook methods
3. Handle errors gracefully
4. Use logging instead of print
5. Keep plugins focused on single concerns
6. Test plugins independently
7. Make configuration optional
8. Follow naming conventions

## Plugin Lifecycle

Hooks are called in this order:
1. `after_config_loaded`
2. `before_build`
3. `after_pages_discovered`
4. `after_collections_loaded`
5. `after_routes_built`
6. `after_build`

## Advanced Plugins

### Using External Libraries

```python
import requests

class APICallPlugin(BasePlugin):
    def after_build(self, site, config, fs_manager):
        response = requests.get('https://api.example.com/data')
        site.data['api_data'] = response.json()
```

### File Watching

```python
import time

class WatchPlugin(BasePlugin):
    def after_build(self, site, config, fs_manager):
        # Monitor files and trigger rebuilds
        pass
```

### Integration Plugins

```python
class AnalyticsPlugin(BasePlugin):
    def after_routes_built(self, site, config, fs_manager):
        # Add analytics tracking to pages
        for page in site.pages:
            page.metadata['analytics_id'] = 'GA-XXXXX'
```

## Testing Plugins

Create `tests/test_my_plugin.py`:

```python
import pytest
from plugins.my_plugin import MyPlugin

def test_plugin_initialization():
    plugin = MyPlugin()
    assert plugin is not None

def test_hook_execution():
    plugin = MyPlugin()
    # Mock site, config, etc.
    plugin.after_config_loaded(site, config, fs_manager, extension_manager)
```

## Distribution

To share plugins:
1. Package as Python module
2. Document installation
3. Provide configuration examples
4. Include tests
5. Add to plugin registry (future feature)