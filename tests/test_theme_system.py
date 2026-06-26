import os
import sys
from pathlib import Path
import tempfile

import pytest


from core.config import Config  # noqa: E402
from core.theme_manager import ThemeManager  # noqa: E402
from engines.factory import create_template_engine  # noqa: E402
from utils.fs_manager import FileSystemManager  # noqa: E402


def test_theme_manager_loads_manifest_and_tokens():
    config = Config()
    # Point project theme settings at a non-existent file so the test is not
    # coupled to the repo's theme.settings.yaml token overrides.
    config.settings["theme"]["settings"] = "./__no_such_theme_settings__.yaml"
    manager = ThemeManager(config, FileSystemManager())

    assert manager.manifest["name"] == "minimal-blog"
    assert "document" in manager.manifest["layouts"]
    # With no project override, resolved tokens equal the theme manifest tokens.
    assert manager.get_resolved_tokens()["colors"]["accent"] == (
        manager.manifest["tokens"]["colors"]["accent"]
    )


def test_theme_manager_generates_theme_css_and_override_file():
    with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        temp_path = Path(temp_dir)
        theme_settings = temp_path / "theme.settings.yaml"
        theme_settings.write_text(
            """
preset: default
tokens:
  colors:
    accent: "#ff0000"
""",
            encoding="utf-8",
        )
        site_theme_dir = temp_path / "site-theme"
        (site_theme_dir / "styles").mkdir(parents=True, exist_ok=True)
        (site_theme_dir / "styles" / "overrides.css").write_text(
            ".custom { color: red; }", encoding="utf-8"
        )

        config = Config()
        config.settings["theme"]["settings"] = str(theme_settings)
        config.settings["theme"]["site_theme_dir"] = str(site_theme_dir)

        manager = ThemeManager(config, FileSystemManager())
        output_dir = temp_path / "output"
        manager.prepare_theme_output(output_dir)

        assert (output_dir / "styles" / "theme.css").exists()
        assert "--colors-accent: #ff0000;" in (
            output_dir / "styles" / "theme.css"
        ).read_text(encoding="utf-8")
        assert (output_dir / "styles" / "theme-overrides.css").exists()


def test_render_blocks_uses_theme_templates():
    config = Config()
    manager = ThemeManager(config, FileSystemManager())
    engine = create_template_engine("django", manager.get_template_dirs())

    html = manager.render_blocks(
        [
            {
                "type": "hero",
                "content": {
                    "title": "Block Title",
                    "text": "Block body",
                },
            }
        ],
        engine,
        {"stylesheets": [], "scripts": [], "navigation_items": [], "site_name": "Test"},
    )

    assert "Block Title" in html
    assert "Block body" in html


def test_site_theme_override_has_template_priority():
    with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        temp_path = Path(temp_dir)
        site_theme_dir = temp_path / "site-theme"
        (site_theme_dir / "partials").mkdir(parents=True, exist_ok=True)
        (site_theme_dir / "partials" / "header.html").write_text(
            "<header>Override Header</header>", encoding="utf-8"
        )

        config = Config()
        config.settings["theme"]["site_theme_dir"] = str(site_theme_dir)
        manager = ThemeManager(config, FileSystemManager())
        engine = create_template_engine("django", manager.get_template_dirs())

        rendered = engine.render(
            "partials/header.html",
            {"navigation_items": [], "site_name": "Test", "stylesheets": [], "scripts": []},
        )

        assert "Override Header" in rendered


def test_invalid_project_component_presets_are_ignored_for_other_themes():
    with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        temp_path = Path(temp_dir)
        theme_settings = temp_path / "theme.settings.yaml"
        theme_settings.write_text(
            """
preset: default
presets:
  header: default
  footer: default
  cards: elevated
  blog_index: magazine
  post: prose
  buttons: rounded
""",
            encoding="utf-8",
        )

        config = Config()
        config.settings["theme"]["name"] = "sunlit-notes"
        config.settings["theme"]["settings"] = str(theme_settings)

        manager = ThemeManager(config, FileSystemManager())

        assert manager.get_component_presets()["header"] == "tabs"
        assert manager.get_component_presets()["footer"] == "notebook"


@pytest.mark.parametrize(
    "theme_name",
    ["docs-basic", "editorial-ledger", "midnight-zine", "sunlit-notes"],
)
def test_new_blog_themes_render_document_layout(theme_name):
    config = Config()
    config.settings["theme"]["name"] = theme_name

    manager = ThemeManager(config, FileSystemManager())
    engine = create_template_engine("django", manager.get_template_dirs())
    base_context = {
        "stylesheets": [],
        "scripts": [],
        "navigation_items": [],
        "site_name": "Test Site",
        "page_url": "https://example.com/blog/sample-post/",
        "page_description": "Sample summary",
        "page_title": "Sample Post",
        "page_summary": "Sample summary",
        "page_type": "blog",
        "page_date": "2026-03-20",
        "collection": "blog",
        "content": "<p>Body copy</p>",
        "body_class": "",
        "container_class": "",
    }

    rendered_blocks = manager.render_blocks(
        [
            {
                "type": "hero",
                "content": {
                    "title": "Block Title",
                    "text": "Block body",
                    "actions": [{"label": "Read more", "url": "/blog/"}],
                },
            }
        ],
        engine,
        base_context,
    )

    rendered = engine.render(
        manager.resolve_layout("document"),
        {
            **base_context,
            "rendered_blocks": rendered_blocks,
        },
    )

    assert manager.manifest["name"] == theme_name
    assert "Sample Post" in rendered
    assert "Block body" in rendered
