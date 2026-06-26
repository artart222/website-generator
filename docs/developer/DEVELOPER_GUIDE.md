# Developer Guide

This guide explains how the current codebase works, where extension points live, and which legacy compatibility paths still exist.

## Overview

The generator is a build-time system. It reads source content, applies processors and plugins, renders with Django templates, optionally exports JSON and frontend artifacts, and writes the final site into `output/`.

Main capabilities:

1. File-based content in `source/`
2. Collection-aware routing
3. Theme manifests plus project-level overrides
4. Plugin hooks throughout the build lifecycle
5. Optional JSON export
6. Optional Tailwind build
7. Optional React export for one collection

## Repository Map

The codebase is a **monorepo** of installable Python packages under `packages/`:

| Package | Path | Role |
|---------|------|------|
| `wg-contracts` | `packages/wg-contracts/` | Shared ports, adapter types, `BaseExtension` |
| `wg-core` | `packages/wg-core/` | SSG build pipeline, config, themes, plugins |
| `wg-runtime` | `packages/wg-runtime/` | Django commerce runtime |
| `wg-commerce` | `packages/wg-commerce/` | Commerce extension (blocks, checkout UI) |

Install for development: `python scripts/install_editable.py` (or install each `packages/*` package with `pip install -e` before the repo root).

Key areas of the repo:

1. `cli.py`
   Primary command-line entry point for `wg` (root meta-package)

2. `packages/wg-core/core/`
   Config loading, project orchestration, routing, theme management, site model, and page model

3. `packages/wg-core/processor/`
   Content processors plus Tailwind and React build helpers

4. `packages/wg-core/engines/`
   Template engine abstraction and Django implementation

5. `packages/wg-core/plugins/`
   Plugin base class and built-in plugins

6. `themes/`
   Packaged themes with manifests, layouts, blocks, partials, styles, and static assets

7. `site-theme/`
   Project-local overrides that take precedence over packaged theme files

8. `source/`
   Source content and data

9. `tests/`
   Coverage for config normalization, collections, theme system, CLI behavior, and frontend helpers

## Entry Points

The preferred entry point is the CLI:

```bash
wg build
wg serve --build-first
wg watch
```

The script entry point is defined in `pyproject.toml`:

```toml
[project.scripts]
wg = "cli:main"
```

Other executable files still present:

1. `main.py`
   Thin build wrapper that loads `config.yaml` and runs `Project.build()`

2. `dev.py`
   Older convenience script that cleans the output directory, calls `main.py`, and serves the result

These files still work, but the CLI is the current public interface.

## Configuration Model

The current public config format is the nested v1 schema:

1. `site`
2. `content`
3. `theme`
4. `build`
5. `plugins`
6. `experimental`

`core/config.py` is responsible for:

1. Loading YAML
2. Merging defaults into a single nested v2 schema
3. Validating into typed `AppConfig` via `core/config_schema.py`
4. Raising `ConfigError` on missing files or invalid YAML (no silent fallback)

Configuration access:

1. Use dotted paths: `config.get("build.output_directory")`
2. Or typed access: `config.schema.build.output_directory`
3. Legacy flat keys and compat aliases are **not** supported in v2

## Plugin hooks

Plugins subclass `BasePlugin` and override lifecycle hooks with `**kwargs`. Common keys:

| Hook | Typical kwargs |
|------|----------------|
| `before_build`, `after_build` | `site`, `config`, `fs_manager` |
| `after_pages_discovered`, `after_collections_loaded` | `site`, `config`, `fs_manager` |
| `before_page_rendered`, `modify_context` | `site`, `config`, `fs_manager`, `page` |

Hooks intentionally stay untyped so plugin authors can ignore unused context.

## Runtime authentication

The Django commerce runtime uses JWT (via `djangorestframework-simplejwt`):

- `POST /token/obtain/` — obtain access/refresh tokens (staff user credentials)
- `POST /token/refresh/` — refresh an access token
- `GET /staff/orders` — staff-only order list (requires `Authorization: Bearer <access>`)

Storefront endpoints remain public (`AllowAny`): checkout, payment callback, catalog snapshot, and public order status by order ID.

## Supporting Guides

Additional repository documentation is available in the `docs/` folder:

- `docs/MIGRATION_GUIDE.md`
- `docs/EXTENSION_AUTHOR_GUIDE.md`
- `docs/THEME_AUTHOR_GUIDE.md`
- `docs/RUNTIME_INTEGRATION_GUIDE.md`
- `docs/RELEASE_CHECKLIST.md`

## Build Lifecycle

The main orchestration happens in `core/project.py`.

`Project.__init__`:

1. Stores config
2. Creates `FileSystemManager`, `Site`, `Router`, `ThemeManager`, and `PluginManager`
3. Loads configured plugins
4. Runs `after_config_loaded`
5. Creates the template engine using the active theme template directories

`Project.build` runs the pipeline in this order:

1. `before_build`
2. `_discover_and_load_pages`
3. `_load_site_data`
4. `_assign_routes`
5. `after_collections_loaded`
6. `after_pages_discovered`
7. `_assign_routes` again so generated pages get canonical paths
8. `after_routes_built`
9. `_render_pages`
10. `_export_json_data`
11. `build_react_section`
12. `_build_tailwind`
13. `_copy_assets`
14. `after_build`

That order matters. For example:

1. Collection index pages are generated before the second route assignment
2. JSON export runs before the React build because the React app consumes that JSON
3. Theme assets are prepared during `_copy_assets`, after page rendering is complete

## Content Processing

Content processors are created in `processor/factory.py`.

Current processor map:

1. `.md` -> `MarkdownProcessor`

Default Markdown extensions:

1. `extra`
2. `meta`
3. `codehilite`

`MarkdownProcessor` also supports YAML front matter surrounded by `---` markers before the Markdown body.

The result of parsing becomes:

1. `Page.processed_content`
2. `Page.metadata`
3. Derived `Page` attributes such as `title`, `slug`, `page_type`, `layout`, `blocks`, and `draft`

## Discovery, Collections, and Routing

Content discovery is collection-first when `content.collections` is configured.

For each collection:

1. The configured `path` is scanned recursively
2. Supported file extensions are matched
3. A `Page` is created and loaded through the correct processor
4. Collection defaults are applied
5. Draft pages are skipped
6. The page is added to `Site`

If no collections are configured, the project falls back to `content.source_directory`.

Routing rules come from `core/router.py`:

1. Home pages render to `output/index.html`
2. 404 pages render to `output/404.html`
3. Collection indexes render to either their configured `index.output_path` or `/<prefix>/index.html`
4. Normal content renders to `/<route.prefix>/<slug>/index.html`

Public URLs are derived from output paths, and `site.base_url` is used to produce absolute URLs.

## Page Model and Template Context

`core/page.py` stores both source metadata and derived build state.

Important page attributes:

1. `title`
2. `slug`
3. `page_type`
4. `summary`
5. `description`
6. `date`
7. `draft`
8. `collection`
9. `layout`
10. `blocks`
11. `output_path`
12. `root_rel_url`
13. `abs_url`

Templates receive context assembled by `Project._build_page_context` and `Page.get_context`.

Important template keys:

1. `content`
2. `rendered_blocks`
3. `page_title`
4. `page_summary`
5. `page_description`
6. `page_keywords`
7. `page_authors`
8. `page_tags`
9. `page_categories`
10. `page_date`
11. `page_url`
12. `page_image`
13. `page_type`
14. `page_layout`
15. `page_layout_options`
16. `page_blocks`
17. `page_meta`
18. `page`
19. `site`
20. `site_data`
21. `navigation_items`
22. `stylesheets`
23. `scripts`
24. `collection`
25. `collection_config`
26. `theme`
27. `theme_manifest`
28. `theme_settings`
29. `theme_tokens`
30. `theme_component_presets`

Plugins may further modify the context through `modify_context` or `modify_template_context`.

## Site Model and Navigation

`core/site.py` holds:

1. Site metadata
2. All pages in memory
3. Loaded structured data
4. Navigation items

Navigation items are built from `site.navigation`.

Resolution order for each item:

1. `url`
2. `collection_index`
3. `type`
4. `collection`

`populate_header()` builds a simple HTML list, but themes usually consume `navigation_items` directly.

## Theme System

`core/theme_manager.py` is the central piece for theme loading and rendering support.

Theme inputs:

1. Packaged theme manifest at `themes/<name>/theme.yaml`
2. Project-level theme settings in `theme.settings.yaml`
3. Project-local overrides in `site-theme/`

Theme template directory precedence:

1. `site-theme/`
2. `themes/<active-theme>/`
3. Any `build.template_dirs`
4. Legacy fallback `templates/<active-theme>/`

Theme responsibilities:

1. Load the manifest and project settings
2. Resolve layouts like `document`, `collection`, and `not_found`
3. Merge theme tokens and selected presets
4. Render block templates
5. Generate `theme.css` from merged tokens
6. Copy packaged assets and project override assets into `output/`

Generated theme output includes:

1. `output/styles/theme-base.css`
2. `output/styles/theme.css`
3. `output/styles/theme-overrides.css` when `site-theme/styles/overrides.css` exists

Legacy note:

`templates/<theme>/` is still supported as a fallback. That makes the old templates directory a compatibility path, not a fully dead subsystem.

## Plugins

Plugins are discovered by scanning `plugins/*.py`, importing modules, and instantiating only the classes whose names appear in `config.plugins`.

Plugin order follows the order listed in config.

Supported hook methods:

1. `after_config_loaded`
2. `before_build`
3. `after_collections_loaded`
4. `before_page_parsed`
5. `after_page_parsed`
6. `after_document_loaded`
7. `after_pages_discovered`
8. `after_routes_built`
9. `before_page_rendered`
10. `after_page_rendered`
11. `after_build`
12. `modify_context`
13. `modify_template_context`
14. `inject_css`
15. `inject_js`

Behavior notes:

1. `run_hook` executes hooks and ignores failures after logging them
2. `run_hook_collect` gathers non-`None` return values in plugin order
3. BasePlugin automatically wraps supported hooks with logging and argument validation

Built-in plugins of note:

1. `CollectionIndexerPlugin`
   Generates synthetic collection index pages

2. `SpecialPagesPlugin`
   Adjusts special routes like the homepage

3. `PageKeyWordExtractor`
   Adds keyword metadata

4. `SitemapPlugin`
   Generates sitemap output

5. `BlogIndexerPlugin`
   Deprecated compatibility plugin kept for older blog-index workflows

## Collection Index Pages

The current preferred approach is `CollectionIndexerPlugin`.

Example:

```yaml
content:
  collections:
    blog:
      path: ./source/blogs
      type: blog
      route:
        prefix: blog
      index:
        enabled: true
        layout: collection
        output_path: blog/index.html
        title: Blog
```

The plugin creates a synthetic `Page` with:

1. `is_generated = True`
2. `is_collection_index = True`
3. `collection = <name>`
4. `page_type = <name>-index`

It generates a simple HTML list from the collection's pages and lets the active theme render that page through the normal collection layout.

## Structured Data Loading

`Project._load_site_data()` scans `content.data_dir` for:

1. `.json`
2. `.yaml`
3. `.yml`

Files are loaded into a nested `site.data` dictionary based on their relative path under the data directory.

Example:

```text
source/data/products/widget.yaml
```

Becomes:

```python
site.data["products"]["widget"]
```

## JSON Export

`Project._export_json_data()` writes JSON when `experimental.export_data.enabled` is true.

Outputs:

1. `site.json`
2. One page JSON file per rendered page

Each page payload includes:

1. `title`
2. `slug`
3. `type`
4. `collection`
5. `abs_url`
6. `root_rel_url`
7. `metadata`
8. `content_html`
9. `blocks`
10. `layout`

If `include_collections` is set, export is filtered to only those collections.

## Tailwind Build

`processor/tailwind_processor.py` handles Tailwind.

When enabled:

1. It reads `experimental.tailwind`
2. It requires `npx` on PATH
3. It runs `tailwindcss -c <config> -i <input> -o <output>`
4. It optionally appends `--minify`

The default output path is `styles/tailwind.css`, which later gets copied into the built site through the normal asset-copy step.

## React / SPA export

Optional React/Next.js export is handled by `core/frontend_manager.py` (not a separate markdown processor).

When `experimental.react.enabled` is true and `experimental.export_data.enabled` is true:

1. The build exports JSON data for configured collections
2. `FrontendManager` wires the React app build and copies output into the site `output/` tree

See `config.yaml` `experimental.react` and `frontend.targets` for paths and env wiring.
3. `NEXT_PUBLIC_COLLECTION`
4. `NEXT_PUBLIC_DATA_URL`

This keeps the React app consuming the same build-generated JSON contract as the rest of the system.

## Asset Copying

Asset copying happens late in the build.

`Project._copy_assets()`:

1. Calls `ThemeManager.prepare_theme_output()`
2. Ensures `./styles` is included in the copy list
3. Copies each configured asset directory into `output/<dir-name>/`

This means:

1. Files in `styles/` become available under `/styles/...`
2. Files in `source/assets/` become available under `/assets/...`
3. Theme assets may also populate `/assets/...`

## Local Development

Preferred local commands:

```bash
wg build
wg serve --build-first
wg watch
pytest
```

You can still use:

```bash
python cli.py build
python main.py
```

But new docs and examples should prefer `wg`.

## Runtime Admin and Roles

The Django runtime includes an intentionally simple first admin surface at `/admin/`.

Bootstrap roles:

```bash
python wg_runtime/manage.py bootstrap_runtime_roles
```

Optional assignment during bootstrap:

```bash
python wg_runtime/manage.py bootstrap_runtime_roles --assign-user <username> --assign-role support
```

Roles currently managed by the bootstrap command:

1. `admin`
2. `editor`
3. `merchandiser`
4. `support`

Current policy boundaries:

1. `Product`, `ProductVariant`, `InventoryItem`, and `MediaAsset` are editable by permitted roles.
2. `Order`, `PaymentAttempt`, and `Refund` are inspection-only in admin.
3. Stock edits on `InventoryItem` create `InventoryAdjustment` rows and `AuditEvent` entries.
4. `AuditEvent` and `InventoryAdjustment` are read-only admin surfaces.

Media uploads use Django's local storage by default:

1. `RUNTIME_MEDIA_ROOT` controls `MEDIA_ROOT`.
2. `RUNTIME_MEDIA_URL` controls `MEDIA_URL`.

## Extension Points

Common extension work happens in:

1. `processor/`
   Add new source format processors

2. `engines/`
   Add new template engines

3. `plugins/`
   Add build-time hooks or template context injections

4. `themes/`
   Add or evolve theme packages

5. `site-theme/`
   Override a packaged theme for one project

6. `config.yaml`
   Add new collections, data sources, or experimental features

## Legacy and Migration Notes

There are still several compatibility paths in the repo:

1. `frontend.*` config aliases are synthesized from v1 config
2. `templates/<theme>/` still acts as a fallback template source
3. `BlogIndexerPlugin` is still present but deprecated
4. `main.py` and `dev.py` still exist as older entry points

These are useful during migration, but new development should center on:

1. `wg`
2. v1 nested config
3. packaged themes in `themes/`
4. project overrides in `site-theme/`
5. collection-based indexes through `CollectionIndexerPlugin`
