from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
import shutil
import time
from slugify import slugify

from core.bootstrap import bootstrap
from core.composition import build_project as compose_project
from core.project import Project
from core.starters import STARTER_NAMES, scaffold_starter
from core.theme_manager import ThemeManager
from utils.fs_manager import FileSystemManager
from wg_runtime.mock_server import serve_mock_runtime

logger = logging.getLogger(__name__)


def build_project(config_path: str = "config.yaml", *, strict: bool = True) -> Project:
    config = bootstrap(config_path)
    if not strict:
        config.settings["build"]["strict"] = False
        config._rebuild_schema()
    project = compose_project(config)
    project.build()
    return project


def cmd_build(args: argparse.Namespace) -> int:
    build_project(args.config, strict=not getattr(args, "lenient", False))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    config = bootstrap(args.config)
    if args.build_first:
        project = compose_project(config)
        project.build()

    output_dir = Path(config.get("build.output_directory", config.get("output_directory")))
    if not output_dir.exists():
        raise FileNotFoundError(
            f"Output directory does not exist: {output_dir}. Run 'wg build' first or use '--build-first'."
        )
    if not output_dir.is_dir():
        raise NotADirectoryError(f"Output path is not a directory: {output_dir}")
    resolved_output = output_dir.resolve()
    handler = partial(SimpleHTTPRequestHandler, directory=str(resolved_output))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    logger.info("Serving %s at http://127.0.0.1:%s", resolved_output, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping server.")
    finally:
        server.server_close()
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    config = bootstrap(args.config)
    watch_paths = _collect_watch_paths(config, Path(args.config))
    last_snapshot = _snapshot_paths(watch_paths)

    logger.info("Starting watch mode.")
    compose_project(config).build()

    try:
        while True:
            time.sleep(args.interval)
            current_snapshot = _snapshot_paths(watch_paths)
            if current_snapshot != last_snapshot:
                logger.info("Detected changes, rebuilding...")
                config = bootstrap(args.config)
                compose_project(config).build()
                watch_paths = _collect_watch_paths(config, Path(args.config))
                current_snapshot = _snapshot_paths(watch_paths)
            last_snapshot = current_snapshot
    except KeyboardInterrupt:
        logger.info("Watch mode stopped.")
        return 0


def cmd_runtime_mock(args: argparse.Namespace) -> int:
    serve_mock_runtime(
        host=args.host,
        port=args.port,
        config_path=args.config,
    )
    return 0


def cmd_runtime_django(args: argparse.Namespace) -> int:
    manage_py = Path(__file__).resolve().parent / "wg_runtime" / "manage.py"
    if not manage_py.exists():
        raise FileNotFoundError(f"Unable to find Django runtime entrypoint: {manage_py}")

    command = [sys.executable, str(manage_py), "runserver", f"{args.host}:{args.port}"]
    process = subprocess.Popen(command)
    try:
        process.wait()
    except KeyboardInterrupt:
        process.terminate()
        process.wait()
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    target_dir = Path(args.directory).resolve()
    fs_manager = FileSystemManager()
    fs_manager.create_directory(target_dir)
    starter_name = getattr(args, "starter", "blog")
    scaffold_starter(target_dir, starter_name, fs_manager)
    return 0


def cmd_new_page(args: argparse.Namespace) -> int:
    return _create_content_file(args, default_collection="pages")


def cmd_new_post(args: argparse.Namespace) -> int:
    return _create_content_file(args, default_collection="blog")


def cmd_theme_create(args: argparse.Namespace) -> int:
    theme_dir = Path("themes") / args.name
    fs_manager = FileSystemManager()
    for relative_dir in [
        "layouts",
        "partials",
        "blocks",
        "styles",
        "assets",
    ]:
        fs_manager.create_directory(theme_dir / relative_dir)

    manifest_path = theme_dir / "theme.yaml"
    if not manifest_path.exists():
        fs_manager.write_file(
            manifest_path,
            f"""name: {args.name}
version: 1
engine: django
layouts:
  base: layouts/base.html
  document: layouts/document.html
  collection: layouts/collection.html
  not_found: layouts/404.html
assets:
  styles:
    base: styles/base.css
  static_dirs:
    - assets
tokens:
  colors:
    bg: "#ffffff"
    surface: "#ffffff"
    text: "#111827"
    muted: "#6b7280"
    accent: "#2563eb"
    border: "#e5e7eb"
  typography:
    body-family: "'Segoe UI', sans-serif"
    heading-family: "'Georgia', serif"
presets:
  default:
    components:
      header: default
      footer: default
      cards: default
      post: default
      buttons: default
blocks:
  core:
    - hero
    - rich_text
    - feature_grid
    - gallery
    - cta
    - faq
  custom: []
supports:
  blocks: true
""",
        )

    _write_if_missing(
        theme_dir / "layouts" / "base.html",
        """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  {% for css_path in stylesheets %}
  <link rel="stylesheet" href="{{ css_path }}">
  {% endfor %}
  <title>{{ page_title }}</title>
</head>
<body>
  {% include "partials/header.html" %}
  <main>{% block content %}{% endblock %}</main>
</body>
</html>
""",
    )
    _write_if_missing(
        theme_dir / "layouts" / "document.html",
        """{% extends "layouts/base.html" %}
{% block content %}
{{ rendered_blocks|safe }}
{{ content|safe }}
{% endblock %}
""",
    )
    _write_if_missing(
        theme_dir / "layouts" / "collection.html",
        """{% extends "layouts/base.html" %}
{% block content %}
<h1>{{ page_title }}</h1>
{{ content|safe }}
{% endblock %}
""",
    )
    _write_if_missing(
        theme_dir / "layouts" / "404.html",
        """{% extends "layouts/base.html" %}
{% block content %}
<h1>404</h1>
<p>Page not found.</p>
{% endblock %}
""",
    )
    _write_if_missing(
        theme_dir / "partials" / "header.html",
        """<header>
  <a href="/">{{ site_name }}</a>
  <nav>
    <ul>
      {% for item in navigation_items %}
      <li><a href="{{ item.url }}">{{ item.title }}</a></li>
      {% endfor %}
    </ul>
  </nav>
</header>
""",
    )
    _write_if_missing(
        theme_dir / "styles" / "base.css",
        """body { background: var(--colors-bg); color: var(--colors-text); font-family: var(--typography-body-family); }
""",
    )
    return 0


def cmd_theme_inspect(args: argparse.Namespace) -> int:
    config = bootstrap(args.config)
    theme_manager = ThemeManager(config, FileSystemManager())
    print(json.dumps(theme_manager.manifest, indent=2))
    return 0


def cmd_theme_eject(args: argparse.Namespace) -> int:
    config = bootstrap(args.config)
    fs_manager = FileSystemManager()
    theme_manager = ThemeManager(config, fs_manager)
    source = theme_manager.theme_dir / args.target
    destination = theme_manager.site_theme_dir / args.target

    if not source.exists():
        raise FileNotFoundError(f"Theme file not found: {source}")
    if destination.exists():
        raise FileExistsError(
            f"Theme override already exists: {destination}. Remove it first if you want to replace it."
        )

    fs_manager.create_directory(destination.parent)
    fs_manager.copy_file(source, destination)
    return 0


def _create_content_file(
    args: argparse.Namespace, default_collection: str
) -> int:
    config = bootstrap(args.config)
    collections = config.get("content.collections", {})
    collection_name = args.collection or default_collection
    collection_cfg = collections.get(collection_name)
    if not isinstance(collection_cfg, dict):
        raise ValueError(f"Collection '{collection_name}' is not configured.")

    collection_path = Path(collection_cfg.get("path", "./source"))
    fs_manager = FileSystemManager()
    fs_manager.create_directory(collection_path)

    slug = slugify(args.slug or args.title)
    file_path = collection_path / f"{slug}.md"
    if file_path.exists():
        raise FileExistsError(
            f"Content file already exists: {file_path}. Choose a different title or pass --slug."
        )
    template = f"""---
title: {args.title}
slug: {slug}
type: {collection_cfg.get('type', collection_name)}
layout: {collection_cfg.get('layout', 'document')}
summary: 
date: {time.strftime('%Y-%m-%d')}
---

# {args.title}

"""
    fs_manager.write_file(file_path, template)
    return 0


def _collect_watch_paths(config, config_path: Path) -> list[Path]:
    paths = [config_path.resolve()]
    for candidate in [
        Path(config.get("content.source_directory", "./source")),
        Path(config.get("content.data_dir", "./source/data")),
        Path(config.get("theme.settings", "./theme.settings.yaml")),
        Path(config.get("theme.site_theme_dir", "./site-theme")),
        Path("themes") / str(config.get("theme.name", "minimal-blog")),
    ]:
        if candidate.exists():
            paths.append(candidate.resolve())
    return paths


def _snapshot_paths(paths: list[Path]) -> dict[str, float]:
    snapshot: dict[str, float] = {}
    for path in paths:
        if path.is_file():
            snapshot[str(path)] = path.stat().st_mtime
            continue
        if path.is_dir():
            for child in path.rglob("*"):
                if child.is_file():
                    snapshot[str(child)] = child.stat().st_mtime
    return snapshot


def _write_if_missing(path: Path, content: str) -> None:
    fs_manager = FileSystemManager()
    if not path.exists():
        fs_manager.write_file(path, content)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wg", description="Website generator CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Build the site")
    build_parser.add_argument("--config", default="config.yaml")
    build_parser.add_argument(
        "--lenient",
        action="store_true",
        help="Continue the build when a plugin or runtime integration fails (default: strict).",
    )
    build_parser.set_defaults(func=cmd_build)

    serve_parser = subparsers.add_parser("serve", help="Serve the output directory")
    serve_parser.add_argument("--config", default="config.yaml")
    serve_parser.add_argument("--port", type=int, default=8000)
    serve_parser.add_argument("--build-first", action="store_true")
    serve_parser.set_defaults(func=cmd_serve)

    watch_parser = subparsers.add_parser("watch", help="Watch content and rebuild")
    watch_parser.add_argument("--config", default="config.yaml")
    watch_parser.add_argument("--interval", type=float, default=1.0)
    watch_parser.set_defaults(func=cmd_watch)

    init_parser = subparsers.add_parser("init", help="Scaffold a new site")
    init_parser.add_argument("directory", nargs="?", default=".")
    init_parser.add_argument("--starter", choices=STARTER_NAMES, default="blog")
    init_parser.set_defaults(func=cmd_init)

    new_page_parser = subparsers.add_parser("new", help="Create a new page or post")
    new_subparsers = new_page_parser.add_subparsers(dest="new_command", required=True)

    page_parser = new_subparsers.add_parser("page", help="Create a page")
    page_parser.add_argument("title")
    page_parser.add_argument("--slug")
    page_parser.add_argument("--collection")
    page_parser.add_argument("--config", default="config.yaml")
    page_parser.set_defaults(func=cmd_new_page)

    post_parser = new_subparsers.add_parser("post", help="Create a post")
    post_parser.add_argument("title")
    post_parser.add_argument("--slug")
    post_parser.add_argument("--collection")
    post_parser.add_argument("--config", default="config.yaml")
    post_parser.set_defaults(func=cmd_new_post)

    theme_parser = subparsers.add_parser("theme", help="Theme tools")
    theme_subparsers = theme_parser.add_subparsers(dest="theme_command", required=True)

    theme_create_parser = theme_subparsers.add_parser("create", help="Create a theme")
    theme_create_parser.add_argument("name")
    theme_create_parser.set_defaults(func=cmd_theme_create)

    theme_inspect_parser = theme_subparsers.add_parser("inspect", help="Inspect the active theme")
    theme_inspect_parser.add_argument("--config", default="config.yaml")
    theme_inspect_parser.set_defaults(func=cmd_theme_inspect)

    theme_eject_parser = theme_subparsers.add_parser("eject", help="Copy a theme file into site-theme")
    theme_eject_parser.add_argument("target")
    theme_eject_parser.add_argument("--config", default="config.yaml")
    theme_eject_parser.set_defaults(func=cmd_theme_eject)

    runtime_parser = subparsers.add_parser("runtime", help="Runtime companion tools")
    runtime_subparsers = runtime_parser.add_subparsers(dest="runtime_command", required=True)

    runtime_mock_parser = runtime_subparsers.add_parser("mock", help="Run the local mock commerce runtime")
    runtime_mock_parser.add_argument("--config", default="config.yaml")
    runtime_mock_parser.add_argument("--host", default="127.0.0.1")
    runtime_mock_parser.add_argument("--port", type=int, default=8787)
    runtime_mock_parser.set_defaults(func=cmd_runtime_mock)

    runtime_django_parser = runtime_subparsers.add_parser("django", help="Run the local Django commerce runtime")
    runtime_django_parser.add_argument("--host", default="127.0.0.1")
    runtime_django_parser.add_argument("--port", type=int, default=8787)
    runtime_django_parser.set_defaults(func=cmd_runtime_django)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
