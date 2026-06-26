# Migration Guide

This guide helps migrate older site configurations and build setups to the current generator version.

## Supported configuration versions

- `version: 2` is **required** for new sites.
- v1 flat configs are no longer normalized automatically; migrate to the nested schema below.

## What changed

The generator uses a nested configuration shape with explicit sections for `site`, `content`, `theme`, and `build`.

Legacy flat keys such as `output_directory`, `template_dirs`, and top-level `frontend` are **not** accepted. Use nested paths instead (for example `build.output_directory`).

## Migrate an existing config file

1. Update the root `version` field to `2`:

```yaml
version: 2
```

2. Move site metadata into `site`:

```yaml
site:
  name: My Site
  base_url: https://example.com
  description: Content-driven storefront and blog
```

3. Move content settings into `content`:

```yaml
content:
  source_directory: ./source
  collections:
    blog:
      path: ./source/blogs
      type: blog
      route:
        prefix: blog
```

4. Move theme config into `theme`:

```yaml
theme:
  name: minimal-blog
  settings: ./theme.settings.yaml
  site_theme_dir: ./site-theme
```

5. Keep build-level settings under `build`:

```yaml
build:
  output_dir: ./output
  static_dir: ./static
```

## Runtime integration migration

If your project uses runtime-backed catalogs or runtime targets, verify these sections are defined under `runtime:` and reference the correct target names.

Example runtime catalog snapshot config:

```yaml
runtime:
  targets:
    - name: commerce-api
      type: django_service
      public_base_url: http://localhost:8787
  catalog_snapshot:
    enabled: true
    target: commerce-api
    url_path: /catalog/snapshot
    output_dir: ./output/data/runtime
```

## Validate your migrated config

- Run `wg build` locally.
- Confirm the site generates without warnings.
- Check that theme overrides still resolve from `site-theme/`.
- Confirm `content.collections` routes still map to the expected output paths.

## Troubleshooting

- If pages stop rendering, verify `layout` values still match active theme layout names.
- If assets are missing, confirm `theme.settings.yaml` and `site_theme_dir` are correct.
- If runtime content is missing, ensure `runtime.targets` and `catalog_snapshot.target` are aligned.
