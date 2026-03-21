import os
import sys
from pathlib import Path
from unittest.mock import Mock

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from core.config import Config  # noqa: E402


def test_config_initialization_uses_v1_defaults():
    config = Config()

    assert config.get("version") == 1
    assert config.get("site.name") == "Website Generator"
    assert config.get("theme.name") == "minimal-blog"
    assert config.get("build.template_engine") == "django"


def test_dotted_get_returns_nested_values():
    config = Config()
    assert config.get("theme.site_theme_dir") == "./site-theme"
    assert config.get("experimental.export_data.enabled") is False


def test_legacy_config_is_normalized_to_v1_shape():
    mock_fs = Mock()
    mock_fs.read_file.return_value = """
    site_name: Test Site
    output_directory: ./dist
    frontend:
      theme: shop-theme
      assets:
        css:
          - /styles/custom.css
    foo: bar
    """

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))

    assert config.get("version") == 1
    assert config.get("site.name") == "Test Site"
    assert config.get("build.output_directory") == "./dist"
    assert config.get("theme.name") == "shop-theme"
    assert config.get("theme.extra_css_urls") == ["/styles/custom.css"]
    assert config.foo == "bar"  # type: ignore[attr-defined]


def test_v1_config_load_preserves_nested_sections():
    mock_fs = Mock()
    mock_fs.read_file.return_value = """
    version: 1
    site:
      name: V1 Site
    content:
      collections:
        blog:
          path: ./content/blog
          type: blog
          route:
            prefix: blog
    theme:
      name: docs-basic
    """

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))

    assert config.get("site.name") == "V1 Site"
    assert config.get("content.collections.blog.route.prefix") == "blog"
    assert config.get("theme.name") == "docs-basic"


def test_unknown_top_level_v1_key_is_retained():
    mock_fs = Mock()
    mock_fs.read_file.return_value = """
    version: 1
    site:
      name: Demo
    experimental_feature: true
    """

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))

    assert config.get("experimental_feature") is True


def test_config_load_missing_file_does_not_crash():
    mock_fs = Mock()
    mock_fs.read_file.side_effect = FileNotFoundError

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))

    assert config.get("build.output_directory") == "./output"
