# User Guide

This guide is for end users who want to build a site with this generator. You do not need to understand the internal architecture to use it.

**What You Get**

1. A static website generated into `output/`
2. Theme-based templates
3. Markdown content support
4. Optional Tailwind CSS build
5. Optional React section for one collection

**Prerequisites**

1. Python 3.10+  
2. Install Python dependencies:
```
pip install -r requirements.txt
```
3. Optional for Tailwind or React:
   - Node.js and npm

**Quick Start**

1. Create content files inside `source/`
2. Configure `config.yaml`
3. Build:
```
python main.py
```
4. Serve the output folder:
```
python -m http.server 8000 --directory output
```
5. Visit:
```
http://localhost:8000/
```

**Content Files**

Use Markdown with frontmatter at the top.
Example file: `source/blogs/first-post.md`
```markdown
---
title: My First Post
slug: my-first-post
type: blog
template: post.html
description: Intro post
---

Hello world. This is my first post.
```

If `type` is missing, the collection default is used.

**Collections (Content Types)**

Collections tell the generator where to find different types of content.
Example:
```yaml
collections:
  blog:
    path: ./source/blogs
    type: blog
    template: post.html
    url_prefix: blog
    index:
      enabled: true
      template: blog-indexer.html
      output_path: blog-indexer/index.html
      title: Blog
```

Result:
```
output/blog/<slug>/index.html
```

**Templates and Themes**

Templates live inside theme folders:
```
templates/blog-theme/
```

Each theme should include:
1. `base.html` with `{% block content %}`
2. `post.html` extending `base.html`
3. `blog-indexer.html` (if you use collection index pages)
4. Optional partials in `partials/`

Switch themes in `config.yaml`:
```yaml
frontend:
  theme: blog-theme
```

If `template_dirs` is not set, it will use `templates/<frontend.theme>/`.

**Assets and Styles**

Assets are copied to `output/` from:
1. `styles/`
2. `asset_dirs` in `config.yaml`

Example:
```yaml
asset_dirs:
  - ./source/assets
```

In templates, CSS and JS are injected via `stylesheets` and `scripts`:
```html
{% for css in stylesheets %}
  <link rel="stylesheet" href="{{ css }}">
{% endfor %}
```

**Using Tailwind CSS (Optional)**

Tailwind builds into `styles/tailwind.css`.

Config:
```yaml
frontend:
  tailwind:
    enabled: true
    input: ./styles/tailwind.input.css
    output: ./styles/tailwind.css
    config: ./tailwind.config.js
    minify: false
```

CSS-first entry file: `styles/tailwind.input.css`:
```css
@import "tailwindcss";
@config "./tailwind.config.js";
@source "./templates/**/*.{html}";
@source "./source/**/*.{md,html}";
```

If you want to use plain CSS only:
1. Set `frontend.tailwind.enabled: false`
2. Add your own CSS files to `frontend.assets.css`

**React Section (Optional)**

You can render one collection as a Next.js static export.

Config:
```yaml
react:
  enabled: true
  collection: shop
  app_dir: ./react-app
  export_subdir: shop
  base_path: /shop
  asset_prefix: /shop
```

Important notes:
1. `frontend.export_data.enabled` must be true
2. Build runs `npm run build` in `react-app`
3. The React site is copied to `output/<export_subdir>/`

After build:
```
http://localhost:8000/shop/
```

**JSON Export (Optional)**

If enabled, the generator writes JSON data for each page.
Config:
```yaml
frontend:
  export_data:
    enabled: true
    output_dir: ./output/data
    include_collections: []
```

This produces:
1. `output/data/site.json`
2. `output/data/<page_path>/page.json`

**Navigation**

Navigation is declared in `config.yaml`:
```yaml
navigation:
  - title: Home
    type: index
  - title: Blog
    type: blog-index
  - title: Shop
    url: /shop/
```

If you set `url`, it uses that directly. Otherwise it matches by `type`.

**Recommended Project Workflow**

1. Add Markdown content to `source/`
2. Adjust `config.yaml` for theme, collections, and assets
3. Run `python main.py`
4. Open `output/` in a local server or deploy it

**Common Issues**

1. 404s in `/shop/` routes
   - Make sure React build is enabled and completed
   - Confirm `output/shop/` exists after build

2. Tailwind styles missing
   - Ensure `frontend.tailwind.enabled: true`
   - Check `styles/tailwind.css` exists after build

3. Links look wrong inside the React section
   - Keep `react.base_path` and `react.export_subdir` aligned

If you want help, provide your `config.yaml` and the build log output.
