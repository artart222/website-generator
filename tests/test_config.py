import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

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


def test_validate_warns_on_v1_config():
    mock_fs = Mock()
    mock_fs.read_file.return_value = """
    version: 1
    site:
      name: Legacy Site
    """

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))
    config.validate()

    assert any("deprecated" in warning.lower() for warning in config.warnings)


def test_validate_rejects_non_django_template_engine():
    mock_fs = Mock()
    mock_fs.read_file.return_value = """
    version: 2
    build:
      template_engine: jinja
    """

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))
    with pytest.raises(ValueError, match="Unsupported template engine"):
        config.validate()


def test_validate_warns_on_fastapi_service_runtime_target():
    mock_fs = Mock()
    mock_fs.read_file.return_value = """
    version: 2
    runtime:
      targets:
        - name: api
          type: fastapi_service
    """

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))
    config.validate()

    assert any("fastapi_service" in warning for warning in config.warnings)


def test_validate_accepts_django_service_runtime_target():
    mock_fs = Mock()
    mock_fs.read_file.return_value = """
    version: 2
    runtime:
      targets:
        - name: api
          type: django_service
    """

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))
    config.validate()

    assert not any("deprecated" in warning.lower() for warning in config.warnings)


def test_validate_warns_when_runtime_catalog_collection_has_snapshot_disabled():
    mock_fs = Mock()
    mock_fs.read_file.return_value = """
    version: 2
    content:
      collections:
        shop:
          type: runtime_catalog
          route:
            prefix: shop
    runtime:
      targets:
        - name: commerce-api
          type: django_service
          public_base_url: http://localhost:8787
    """

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))
    config.validate()

    assert any(
        "type 'runtime_catalog'" in warning
        for warning in config.warnings
    )


def test_validate_accepts_runtime_catalog_when_snapshot_enabled_and_target_exists():
    mock_fs = Mock()
    mock_fs.read_file.return_value = """
    version: 2
    content:
      collections:
        shop:
          type: runtime_catalog
          model: product
          route:
            prefix: shop
    runtime:
      targets:
        - name: commerce-api
          type: django_service
          public_base_url: http://localhost:8787
      catalog_snapshot:
        enabled: true
        target: commerce-api
        url_path: /catalog/snapshot
        output_dir: ./output/data/runtime
    """

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))
    config.validate()

    assert not any(
        "type 'runtime_catalog'" in warning
        for warning in config.warnings
    )
    assert not any(
        "was not found in runtime.targets[].name" in warning
        for warning in config.warnings
    )


def test_list_files_returns_sorted_paths():
    from utils.fs_manager import FileSystemManager

    fs_manager = FileSystemManager()
    with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        temp_path = Path(temp_dir)
        (temp_path / "b.md").write_text("b content", encoding="utf-8")
        (temp_path / "a.md").write_text("a content", encoding="utf-8")

        found_files = fs_manager.list_files(temp_path, recursive=False)

        assert [p.name for p in found_files] == ["a.md", "b.md"]
