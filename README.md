# Website Generator

A modular **Python** website generator with a pluggable architecture, theming via templates, and simple YAML configuration.

> MIT Licensed. See [LICENSE](./LICENSE).

---

## Features

- **Modular core** with clear layers (`core/`, `processor/`, `utils/`) for maintainability.
- **Extensible** via `engines/` and `plugins/` directories so you can add or swap functionality without touching the core.
- **Theming & layout** using templates (see `templates/blog-template/`) and site-wide styles in `styles/`.
- **Single entry point**: run the generator from `main.py`.
- **Human-readable config** via `config.yaml`.

## Quickstart

```bash
# 1) Clone
git clone https://github.com/artart222/website-generator.git
cd website-generator

# 2) (Recommended) Create a virtual environment
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3) Install dependencies
pip install -r requirements.txt

# 4) Configure your site
#    Edit config.yaml to point to your content, templates, and output paths

# 5) Generate the site
python main.py
```


## Project Structure

```
website-generator/
├─ core/                 # Core building blocks used by the generator
├─ engines/              # Pluggable "engines" the generator can use
├─ plugins/              # Optional features you can enable/extend
├─ processor/            # Processing pipeline / transforms
├─ source/               # Your site’s source content (add your files here)
├─ styles/               # Global CSS and assets for themes
├─ templates/
│  └─ blog-template/     # Example template/theme
├─ utils/                # Shared helpers and utilities
├─ config.yaml           # Site configuration
├─ main.py               # Entry point
├─ requirements.txt      # Python dependencies
└─ LICENSE               # MIT
```
