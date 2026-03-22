import os
import sys
from pathlib import Path
import tempfile

import pytest

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from cli import build_parser, cmd_init, cmd_new_post, cmd_theme_create, cmd_theme_eject  # noqa: E402


def test_cli_parser_supports_theme_eject():
    parser = build_parser()
    args = parser.parse_args(["theme", "eject", "partials/header.html"])
    assert args.target == "partials/header.html"


def test_theme_create_scaffolds_manifest(monkeypatch):
    with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        temp_path = Path(temp_dir)
        original_cwd = Path.cwd()
        monkeypatch.chdir(temp_path)
        cmd_theme_create(type("Args", (), {"name": "demo-theme"})())
        monkeypatch.chdir(original_cwd)

        assert (temp_path / "themes" / "demo-theme" / "theme.yaml").exists()
        assert (temp_path / "themes" / "demo-theme" / "layouts" / "base.html").exists()


def test_init_creates_expected_support_directories(monkeypatch):
    with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        temp_path = Path(temp_dir)
        target = temp_path / "site"
        original_cwd = Path.cwd()
        monkeypatch.chdir(temp_path)

        cmd_init(type("Args", (), {"directory": str(target)})())

        monkeypatch.chdir(original_cwd)

        assert (target / "source" / "assets").exists()
        assert (target / "source" / "data").exists()
        assert (target / "styles").exists()


def test_new_post_refuses_to_overwrite_existing_file():
    with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        temp_path = Path(temp_dir)
        config_path = temp_path / "config.yaml"
        posts_dir = temp_path / "posts"
        posts_dir.mkdir(parents=True, exist_ok=True)
        (posts_dir / "hello-world.md").write_text("existing", encoding="utf-8")
        config_path.write_text(
            f"""
version: 1
content:
  collections:
    blog:
      path: {posts_dir.as_posix()}
      type: blog
      layout: document
""",
            encoding="utf-8",
        )

        args = type(
            "Args",
            (),
            {
                "title": "Hello World",
                "slug": None,
                "collection": None,
                "config": str(config_path),
            },
        )()

        with pytest.raises(FileExistsError):
            cmd_new_post(args)


def test_theme_eject_refuses_to_overwrite_existing_override(monkeypatch):
    with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        temp_path = Path(temp_dir)
        theme_dir = temp_path / "themes" / "minimal-blog" / "partials"
        site_theme_dir = temp_path / "site-theme" / "partials"
        theme_dir.mkdir(parents=True, exist_ok=True)
        site_theme_dir.mkdir(parents=True, exist_ok=True)

        (temp_path / "themes" / "minimal-blog" / "theme.yaml").write_text(
            """
name: minimal-blog
version: 1
engine: django
layouts:
  base: layouts/base.html
  document: layouts/document.html
  collection: layouts/collection.html
  not_found: layouts/404.html
""",
            encoding="utf-8",
        )
        (theme_dir / "header.html").write_text("<header>Theme</header>", encoding="utf-8")
        (site_theme_dir / "header.html").write_text(
            "<header>Override</header>", encoding="utf-8"
        )
        config_path = temp_path / "config.yaml"
        config_path.write_text(
            f"""
version: 1
theme:
  name: minimal-blog
  site_theme_dir: {(temp_path / 'site-theme').as_posix()}
""",
            encoding="utf-8",
        )

        original_cwd = Path.cwd()
        monkeypatch.chdir(temp_path)
        try:
            with pytest.raises(FileExistsError):
                cmd_theme_eject(
                    type(
                        "Args",
                        (),
                        {
                            "target": "partials/header.html",
                            "config": str(config_path),
                        },
                    )()
                )
        finally:
            monkeypatch.chdir(original_cwd)
