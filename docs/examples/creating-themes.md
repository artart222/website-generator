# Creating Custom Themes

This tutorial shows how to create a custom theme for the Website Generator.

## Theme Structure

Themes live in the `themes/` directory. Each theme is a directory containing:

```
themes/my-theme/
├── manifest.yaml          # Theme metadata
├── layouts/               # Template layouts
│   ├── document.html
│   └── page.html
├── partials/              # Reusable template parts
│   ├── header.html
│   └── footer.html
├── styles/                # CSS files
│   └── main.css
└── blocks/                # Content blocks
    └── hero.html
```

## Step 1: Create Theme Directory

```bash
mkdir themes/my-theme
cd themes/my-theme
```

## Step 2: Create Manifest

Create `manifest.yaml`:

```yaml
name: my-theme
version: 1.0.0
description: My custom theme
author: Your Name

layouts:
  - document
  - page

partials:
  - header
  - footer
  - navigation

blocks:
  - hero
  - content
  - sidebar

styles:
  - main.css
```

## Step 3: Create Layouts

Layouts define the overall page structure.

`layouts/document.html`:
```html
<!DOCTYPE html>
<html>
<head>
    <title>{{ page.title }}</title>
    {% include 'partials/header.html' %}
</head>
<body>
    {% include 'partials/navigation.html' %}
    <main>
        {% block content %}{% endblock %}
    </main>
    {% include 'partials/footer.html' %}
</body>
</html>
```

`layouts/page.html`:
```html
{% extends 'layouts/document.html' %}

{% block content %}
<div class="page">
    <h1>{{ page.title }}</h1>
    <div class="content">
        {{ page.processed_content }}
    </div>
</div>
{% endblock %}
```

## Step 4: Create Partials

Partials are reusable components.

`partials/header.html`:
```html
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/styles/main.css">
```

`partials/navigation.html`:
```html
<nav>
    <ul>
        {% for item in site.navigation_items %}
        <li><a href="{{ item.url }}">{{ item.title }}</a></li>
        {% endfor %}
    </ul>
</nav>
```

## Step 5: Create Blocks

Blocks render structured content.

`blocks/hero.html`:
```html
<section class="hero">
    <h1>{{ block.title }}</h1>
    <p>{{ block.text }}</p>
</section>
```

## Step 6: Add Styles

`styles/main.css`:
```css
body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 0;
}

.hero {
    background: #f0f0f0;
    padding: 2rem;
    text-align: center;
}

nav ul {
    list-style: none;
    display: flex;
    gap: 1rem;
    padding: 1rem;
    background: #333;
    margin: 0;
}

nav a {
    color: white;
    text-decoration: none;
}
```

## Step 7: Use the Theme

Update `config.yaml`:

```yaml
theme:
  name: my-theme
```

## Step 8: Test the Theme

```bash
wg build
wg serve --build-first
```

## Advanced Features

### Theme Settings

Add customizable settings in `manifest.yaml`:

```yaml
settings:
  - name: primary_color
    type: string
    default: "#007bff"
  - name: font_size
    type: number
    default: 16
```

Access in templates:
```html
<style>
body { color: {{ theme.settings.primary_color }}; }
</style>
```

### Local Overrides

Override theme files locally in `site-theme/`:

```bash
wg theme eject partials/header.html
# Edit site-theme/partials/header.html
```

### Block System

Use blocks in content:

```md
---
blocks:
  - type: hero
    content:
      title: Welcome
      text: Hello world
---

Regular content here.
```

## Best Practices

1. Use semantic HTML
2. Make layouts flexible
3. Provide good defaults
4. Document customization options
5. Test with different content types
6. Keep CSS modular
7. Use theme settings for customization