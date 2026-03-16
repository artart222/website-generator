# Developer Guide

This guide explains how the generator is structured, how the build pipeline works, and where to extend it. It reflects the current codebase and configuration as of this repository state.

**What This Project Is**

This is a static site generator with:
1. File-based content (`source/`)
2. Template rendering (Django templates)
3. A plugin system for build-time hooks
4. Optional Tailwind CSS build
5. Optional React/Next static export for one collection
6. Optional JSON export for frontend consumption

There is no runtime server. Everything happens at build time and outputs to `output/`.

**Core Architecture**

The pipeline is orchestrated by `core/project.py`:
1. Load config and initialize core objects
2. Discover content and create `Page` objects
3. Load structured data (`site.data`)
4. Render templates
5. Export JSON (optional)
6. Build React section (optional)
7. Build Tailwind CSS (optional)
8. Copy assets

Key types:
1. `core/Config`: Loads `config.yaml`, merges defaults, exposes `settings`
2. `core/Project`: Build orchestrator and integration point
3. `core/Site`: In-memory model of the site, holds pages and site metadata
4. `core/Page`: Represents a single content file and its rendered output
5. `plugins/BasePlugin`: Hook base class and lifecycle hooks
6. `processor/*`: Content processing and Tailwind build

**Build Flow in Detail**

1. `Project.__init__`
   - Loads config
   - Creates `Site`, `PluginManager`, and template engine
   - Runs `after_config_loaded` hooks

2. `Project.build`
   - `before_build` hooks
   - `_discover_and_load_pages`
   - `_load_site_data`
   - `after_pages_discovered` hooks
   - `_render_pages`
   - `_export_json_data` if `frontend.export_data.enabled`
   - `_build_react_section` if `react.enabled`
   - `_build_tailwind` if `frontend.tailwind.enabled`
   - `_copy_assets`
   - `after_build` hooks

**Content Discovery and Collections**

If `collections` exists in `config.yaml`, discovery is collection-based:
1. Each collection defines a `path` and defaults like `type` and `template`
2. Files are scanned inside those collection paths
3. The `page.collection` and `page.collection_config` are set
4. Frontmatter `type` can override collection `type`
5. Output path is `/<url_prefix or type>/<slug>/index.html`

If `collections` is missing, the generator falls back to scanning `source_directory`.

**Template Selection Order**

Template name resolves in this order:
1. Frontmatter `template`
2. Collection `template`
3. `templates_by_type[type]`
4. Fallback `post.html`

See `core/project.py:_resolve_template_name`.

**Template Context**

Context is assembled in `Project._build_page_context` and `Page.get_context`.
Important keys available in templates:
1. `content`, `page_title`, `page_description`, `page_meta`
2. `page`, `site`, `site_data`
3. `frontend`, `theme`
4. `stylesheets`, `scripts`
5. `collection`, `collection_config`
6. `header` (generated navigation HTML)

**Plugins**

Plugins are loaded from `plugins/` and must be listed in `config.yaml` under `plugins`.
The manager preserves the order of `config.plugins`.

Hooks you can implement in a plugin:
1. `after_config_loaded`
2. `before_build`
3. `after_pages_discovered`
4. `before_page_parsed`
5. `after_page_parsed`
6. `before_page_rendered`
7. `after_page_rendered`
8. `after_build`
9. `modify_template_context` (returns dict)
10. `inject_css` (returns list or string)
11. `inject_js` (returns list or string)

See `plugins/base_plugin.py` and `core/plugin_manager.py`.

**Collection Index Pages**

`CollectionIndexerPlugin` generates index pages for collections with:
```
collections:
  blog:
    index:
      enabled: true
      template: blog-indexer.html
      output_path: blog-indexer/index.html
      title: Blog
```

It creates a synthetic `Page` with `type: <collection>-index`.
This is how blog indexes are generated today.

**Static Data Loading**

If `data_dir` is set, JSON/YAML files are loaded into `site.data`.
Example structure:
```
source/data/products/widget.json
```
Becomes:
```
site.data["products"]["widget"]
```

**Tailwind CSS (v4, CSS-first)**

The Tailwind build is handled in `processor/tailwind_processor.py`:
```
npx tailwindcss -c <config> -i <input> -o <output> [--minify]
```

Current CSS-first setup:
1. `styles/tailwind.input.css` imports Tailwind and declares sources
2. `tailwind.config.js` only contains `theme.extend` and plugins

The React app has its own Tailwind input:
`react-app/styles/globals.css`

**React/Next Static Section**

If `react.enabled` is true:
1. JSON export must be enabled
2. JSON is copied into `react-app/public/data`
3. `npm run build` runs in `react-app`
4. `react-app/out` is copied into `output/<export_subdir>`

Environment variables passed into Next build:
1. `NEXT_PUBLIC_BASE_PATH`
2. `NEXT_PUBLIC_ASSET_PREFIX`
3. `NEXT_PUBLIC_COLLECTION`
4. `NEXT_PUBLIC_DATA_URL`

See `core/project.py:_build_react_section`.

**Key Configuration Files**

1. `config.yaml` for site configuration
2. `tailwind.config.js` for Tailwind theme tokens
3. `styles/tailwind.input.css` for Tailwind entrypoint
4. `react-app/next.config.js` for Next static export

**Local Development**

Build:
```
python main.py
```

Serve output:
```
python -m http.server 8000 --directory output
```

If React is enabled, visit:
```
http://localhost:8000/<export_subdir>/
```

**Extension Points**

Common places to extend:
1. New processors in `processor/` and `processor/factory.py`
2. New plugins in `plugins/`
3. New themes in `templates/<theme>/`
4. New collections in `config.yaml`
5. New data sources in `source/data/`

**Design Notes and Current Constraints**

1. Build-time only, no runtime server
2. File-based content model
3. Plugins are build-time hooks only
4. JSON export is the stable interface for frontend consumers

If you plan to move toward a CMS, preserve the JSON contract so a future backend can feed the same schema.
