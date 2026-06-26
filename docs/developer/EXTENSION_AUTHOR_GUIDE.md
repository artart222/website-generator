# Extension Author Guide

This guide explains how to build and register an extension for the website generator.

## Extension package layout

A local extension package should live under `extensions/<name>/` and may include:

- `wg-extension.yaml` — extension manifest
- `extension.py` — Python entrypoint module
- `templates/` — extension-provided templates
- `assets/` — static assets copied into the build output

## Manifest format

A minimal `wg-extension.yaml`:

```yaml
name: my-extension
version: 1
python:
  entrypoint: extensions.my_extension.extension:get_extension
```

If `python.entrypoint` is omitted, the generator will resolve a default entrypoint using the normalized package name.

## Python entrypoint

The entrypoint may expose either:

- a callable that returns an extension instance
- a class whose constructor returns the extension instance

The extension instance should implement optional registration methods such as:

- `register_models(registry)`
- `register_frontend_targets(registry)`
- `register_runtime_adapters(registry)`
- `register_build_hooks(registry)`
- `register_cli_commands(registry)`

Example:

```python
from wg_contracts import BaseExtension

class MyExtension(BaseExtension):
    def register_build_hooks(self, registry):
        registry.register("after_build", self.on_after_build)

    def on_after_build(self, **kwargs):
        print("Extension after_build hook")


def get_extension():
    return MyExtension()
```

## Registration helper methods

Use the provided registries to extend core behavior.

- `registry.register(name, value, metadata=...)` for named definitions
- `registry.register_many(...)` when providing multiple model definitions or adapters
- `BuildHookRegistry.register(hook_name, func)` to run lifecycle hooks

## Template and asset discovery

The generator will include extension-provided `templates/` and `assets/` directories when the extension is loaded.

- `templates/` files are added to the active template search path
- `assets/` are copied into `output/assets/extensions/<slugified-extension-name>/`

## Local path configuration

Local extensions can be located outside `extensions/` by setting `extensions.local_paths` in `config.yaml`.

Example:

```yaml
extensions:
  local_paths:
    - ./extensions
    - ./custom_extensions
  enabled:
    - my-extension
```

## Testing extensions

- Enable the extension in `config.yaml`
- Run `wg build`
- Confirm generated output includes template overrides, assets, or hook-driven content
