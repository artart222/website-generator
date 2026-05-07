# Theme Author Guide

This guide describes how to author a theme package for the website generator.

## Theme structure

A theme package should include:

- `templates/` — Django templates used to render pages
- `styles/` — theme CSS or Tailwind input styles
- `theme.settings.yaml` — optional theme configuration
- `assets/` — static assets copied into the build output

Example structure:

```
themes/my-theme/
  templates/
    base.html
    layouts/
      document.html
      collection.html
  styles/
    tailwind.css
  assets/
    images/
    fonts/
  theme.settings.yaml
```

## Theme settings

`theme.settings.yaml` can define theme-specific defaults, asset paths, and style injection.

Example:

```yaml
theme_name: My Theme
primary_color: #1a202c
extra_css_urls: []
```

## Theme layouts

The generator expects theme layouts to match configured `layout` names.

Common layout names:

- `document`
- `collection`
- `index`
- `product`

Use `base.html` or a shared wrapper template to centralize the page shell and header/footer structure.

## Local overrides

Project-specific overrides live in `site-theme/` and take precedence over packaged theme files.

Example override path:

```
site-theme/templates/layouts/document.html
```

## Rendering conventions

- Use the `content` context variable for rendered page HTML
- Use `page_title`, `page_description`, and `page_url` from the generated page context
- Add theme-specific template blocks for optional sections such as `hero`, `sidebar`, or `footer`

## Assets and static files

Theme `assets/` are copied into the final build output.
Use relative URLs in templates and include assets using the `static` or `asset` helpers provided by the active theme.

## Testing your theme

- Configure the theme name in `config.yaml`
- Run `wg build`
- Confirm rendered pages use the expected theme templates
- Confirm `site-theme/` overrides are applied when present
