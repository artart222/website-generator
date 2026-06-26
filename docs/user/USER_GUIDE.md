# User Guide

This guide is for people using the generator to build a site. It focuses on the current workflow, current config format, and the current theme system.

## What You Get

1. A static website generated into `output/`
2. Markdown content with YAML front matter
3. Collection-based routing for pages like blogs, docs, or shop items
4. Theme packages with project-level overrides
5. Optional JSON export, Tailwind build, and React export for one collection

## Documentation

See the companion guides in `docs/` for extension authors, theme authors, runtime integration, migration planning, and release readiness.

## Prerequisites

1. Python 3.10+
2. Install the project (monorepo — installs all workspace packages in editable mode):

```bash
git clone https://github.com/artart222/website-generator.git
cd website-generator
python scripts/install_editable.py
```

This installs `wg-contracts`, `wg-core`, `wg-runtime`, `wg-commerce`, and the root `website-generator` CLI. A plain `pip install -e .` will not work until those packages are installed; they are not published to PyPI.

3. Optional for Tailwind or React export:
   Node.js and npm

If you do not want to install the CLI entry point, you can run the same commands with `python cli.py ...`.

## Quick Start

Build the sample site already included in this repository:

```bash
wg build
wg serve --build-first
```

Open:

```text
http://127.0.0.1:8000/
```

Rebuild automatically while editing:

```bash
wg watch
```

## Start a New Site

Create a new project scaffold:

```bash
wg init my-site
cd my-site
wg build
wg serve --build-first
```

The scaffold creates:

1. `config.yaml`
2. `theme.settings.yaml`
3. `source/index.md`
4. `source/blogs/hello-world.md`
5. `site-theme/`

## CLI Workflow

Build the site:

```bash
wg build
```

Serve the generated output:

```bash
wg serve --build-first
```

Watch content, theme files, and config for changes:

```bash
wg watch
```

Launch the Django runtime companion:

```bash
wg runtime django
```

## Content Files

Create content files:

```bash
wg new page "About"
wg new post "Release Notes"
wg new post "Version 1.0" --slug version-1-0
```

Theme utilities:

```bash
wg theme inspect
wg theme create my-theme
wg theme eject partials/header.html
```

## Content Files

Content is usually written as Markdown with YAML front matter.

Example page:

```md
---
title: My First Post
summary: Intro post
date: 2026-03-22
type: blog
layout: document
tags:
  - python
  - static-sites
blocks:
  - type: hero
    content:
      title: Welcome
      text: This section is rendered before the Markdown body.
---

# Hello world

This is my first post.
```

Useful front matter fields:

1. `title`
2. `slug`
3. `summary`
4. `description`
5. `date`
6. `type`
7. `layout`
8. `draft`
9. `tags`
10. `blocks`

Notes:

1. `draft: true` skips the page during the build
2. If `type` is missing, the collection default is used
3. If `slug` is missing, one is generated from the title
4. `layout` usually maps to a theme layout such as `document` or `collection`

## Collections

Collections tell the generator where content lives and how it should route.

Example:

```yaml
content:
  collections:
    blog:
      path: ./source/blogs
      type: blog
      route:
        prefix: blog
      layout: document
      index:
        enabled: true
        layout: collection
        output_path: blog/index.html
        title: Blog
    pages:
      path: ./source
      type: page
      route:
        prefix: ""
      layout: document
```

With that setup:

1. Blog posts render to `output/blog/<slug>/index.html`
2. The blog landing page renders to `output/blog/index.html`
3. A page with `type: index` becomes the site homepage at `output/index.html`

## Configuration

The current config format is the nested v1 schema, but `version: 2` is the official default for new projects:

```yaml
version: 2

site:
  name: My Site
  description: Portfolio and blog
  base_url: https://example.com
  author: Your Name
  navigation:
    - title: Home
      type: index
    - title: Blog
      collection_index: blog

content:
  source_directory: ./source
  data_dir: ./source/data
  collections: {}

theme:
  name: minimal-blog
  settings: ./theme.settings.yaml
  site_theme_dir: ./site-theme
  extra_css_urls: []
  extra_js_urls: []

build:
  output_directory: ./output
  asset_dirs:
    - ./source/assets
  template_engine: django
  log_level: 20

plugins: []

experimental:
  export_data:
    enabled: false
  react:
    enabled: false
  tailwind:
    enabled: false
```

Recommendations:

1. Set `site.base_url` to the full deployed URL so absolute URLs and sitemap output are correct
2. Prefer the v1 nested keys above for new projects
3. Keep pages and posts in separate collections once the site grows

## Navigation

Navigation is declared in `site.navigation`.

Example:

```yaml
site:
  navigation:
    - title: Home
      type: index
    - title: Blog
      collection_index: blog
    - title: GitHub
      url: https://github.com/example/repo
```

Navigation items resolve in this order:

1. `url`
2. `collection_index`
3. `type`
4. `collection`

## Themes and Overrides

Themes live in `themes/<theme-name>/`.

Each theme provides:

1. Layouts such as `base`, `document`, `collection`, and `not_found`
2. Partials like headers and footers
3. Block templates like `hero`, `gallery`, or `faq`
4. Theme tokens for colors, typography, spacing, and radius
5. Base CSS and optional static assets

Select a theme in `config.yaml`:

```yaml
theme:
  name: minimal-blog
  settings: ./theme.settings.yaml
  site_theme_dir: ./site-theme
```

Project-specific theme settings live in `theme.settings.yaml`:

```yaml
preset: default
presets: {}
tokens:
  colors:
    accent: "#0f766e"
stylesheets: []
scripts: []
```

Use `site-theme/` when you want to override packaged theme files without editing the theme itself.

Examples:

1. `site-theme/partials/header.html`
2. `site-theme/layouts/document.html`
3. `site-theme/styles/overrides.css`
4. `site-theme/assets/...`

`wg theme eject <path>` copies a file from the active theme into `site-theme/` so you can start customizing it.

## Assets and Styles

The build copies assets from several places:

1. Theme CSS and theme static assets
2. `styles/`
3. Each directory listed in `build.asset_dirs`
4. Optional override assets in `site-theme/assets`

Theme styles are exposed in templates through `stylesheets`, and scripts through `scripts`.

Example template snippet:

```html
{% for css_path in stylesheets %}
<link rel="stylesheet" href="{{ css_path }}">
{% endfor %}
```

## Data Files

Structured data can live in `content.data_dir`, which defaults to `source/data`.

Supported file types:

1. `.json`
2. `.yaml`
3. `.yml`

Example:

```text
source/data/products/widget.yaml
```

Becomes available to templates as:

```text
site_data["products"]["widget"]
```

## JSON Export

Enable JSON output when you want a headless or hybrid frontend:

```yaml
experimental:
  export_data:
    enabled: true
    output_dir: ./output/data
    include_collections: []
```

This writes:

1. `output/data/site.json`
2. One `page.json` for each generated page

If `include_collections` is non-empty, only those collections are exported.

## Tailwind CSS

Tailwind support is optional and requires Node.js.

Enable it in `config.yaml`:

```yaml
experimental:
  tailwind:
    enabled: true
    input: ./styles/tailwind.input.css
    output: ./styles/tailwind.css
    config: ./tailwind.config.js
    minify: false
```

The build runs Tailwind and writes the compiled file to `styles/tailwind.css`, which is then copied into the final output.

## React Export

One collection can be rendered through the bundled Next.js app in `react-app/`.

Example:

```yaml
experimental:
  export_data:
    enabled: true
  react:
    enabled: true
    collection: shop
    app_dir: ./react-app
    export_subdir: shop
    base_path: /shop
    asset_prefix: /shop
```

Important notes:

1. React export requires `experimental.export_data.enabled: true`
2. The build copies JSON data into `react-app/public/data`
3. `npm run build` runs inside `react-app`
4. The static export is copied into `output/<export_subdir>/`

After build, the React section is typically available at:

```text
http://127.0.0.1:8000/shop/
```

## Recommended Workflow

1. Start with `wg init` or the sample repository structure
2. Define collections in `config.yaml`
3. Add Markdown content in `source/`
4. Pick a theme and adjust `theme.settings.yaml`
5. Override only the files you need in `site-theme/`
6. Run `wg watch` while editing
7. Build with `wg build` before deploy

## Common Issues

1. `wg serve` fails because `output/` does not exist
   Run `wg build` first, or use `wg serve --build-first`

2. A navigation link does not render
   Check whether the target page or collection index actually exists

3. Tailwind styles are missing
   Make sure `experimental.tailwind.enabled: true` is set and Node.js is installed

4. React pages 404
   Confirm React export is enabled, JSON export is enabled, and `output/<export_subdir>/` exists after the build

5. Theme override is ignored
   Check that the override file path inside `site-theme/` matches the theme file path exactly

## Related Docs

1. `README.md` for the fastest overview
2. `docs/developer/DEVELOPER_GUIDE.md` for architecture and extension details
3. `ARCHITECTURE.md` for broader design notes
