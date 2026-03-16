# import os
# from pathlib import Path
# import sys


# # Add project root to Python path
# current_dir = os.path.dirname(os.path.abspath(__file__))
# project_root = os.path.dirname(current_dir)  # Go up one level from tests/
# sys.path.insert(0, project_root)

# from unittest.mock import Mock  # noqa: E402
# from core.config import Config  # noqa: E402


# def test_config_initialization_with_defaults():
#     """Test that Config initializes with correct default values."""
#     # Act
#     config = Config()

#     # Assert
#     assert config.settings["source_directory"] == "./source"
#     assert config.settings["output_directory"] == "./output"
#     assert config.settings["template_engine"] == "django"


# def test_config_load_from_file():
#     """Test loading configuration from a YAML file."""
#     # Arrange
#     mock_fs_manager = Mock()
#     # config_data = {"site_name": "Test Site", "output_directory": "./build"}

#     # Mock the read_file method to return YAML content
#     mock_fs_manager.read_file.return_value = """
#     site_name: Test Site
#     output_directory: ./build
#     """

#     config = Config(fs_manager=mock_fs_manager)

#     # Act
#     config.load(Path("config.yaml"))

#     # Assert
#     assert config.settings["site_name"] == "Test Site"
#     assert config.settings["output_directory"] == "./build"
#     mock_fs_manager.read_file.assert_called_once_with(Path("config.yaml"))


# def test_config_get_and_set_methods():
#     """Test getting and setting configuration values."""
#     # Arrange
#     config = Config()

#     # Act - Test get method
#     source_dir = config.get("source_directory")

#     # Assert
#     assert source_dir == "./source"

#     # Act - Test set method
#     config.set("new_setting", "new_value")

#     # Assert
#     assert config.get("new_setting") == "new_value"
#     assert config.settings["new_setting"] == "new_value"


import os
import sys
from pathlib import Path
from unittest.mock import Mock

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from core.config import Config  # noqa: E402


def test_config_initialization_with_defaults():
    config = Config()

    assert config.settings["source_directory"] == "./source"
    assert config.settings["output_directory"] == "./output"
    assert config.settings["template_engine"] == "django"
    assert config.settings["template_dirs"] == ["./templates/blog-theme/"]


def test_default_keys_are_synced_as_attributes():
    config = Config()

    assert config.source_directory == "./source"  # type: ignore
    assert config.output_directory == "./output"  # type: ignore
    assert config.template_engine == "django"  # type: ignore
    assert config.template_dirs == ["./templates/blog-theme/"]  # type: ignore


def test_config_load_from_file_overrides_defaults():
    mock_fs = Mock()
    mock_fs.read_file.return_value = """
    site_name: Test Site
    output_directory: ./build
    """

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))

    assert config.settings["site_name"] == "Test Site"
    assert config.settings["output_directory"] == "./build"


def test_config_load_calls_fs_manager_with_path():
    mock_fs = Mock()
    mock_fs.read_file.return_value = ""

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))

    mock_fs.read_file.assert_called_once_with(Path("config.yaml"))


def test_config_load_merges_with_existing_settings():
    mock_fs = Mock()
    mock_fs.read_file.return_value = """
    site_name: My Site
    """

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))

    # Loaded value
    assert config.settings["site_name"] == "My Site"

    # Defaults preserved
    assert config.settings["source_directory"] == "./source"


def test_config_deep_merge_preserves_frontend_defaults():
    mock_fs = Mock()
    mock_fs.read_file.return_value = """
    frontend:
      tailwind:
        enabled: false
    """

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))

    assert config.settings["frontend"]["tailwind"]["enabled"] is False
    assert config.settings["frontend"]["assets"]["css"] == [
        "/styles/tailwind.css",
        "/styles/code.css",
    ]


def test_template_dirs_derived_from_frontend_theme_when_not_set():
    mock_fs = Mock()
    mock_fs.read_file.return_value = """
    frontend:
      theme: shop-theme
    """

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))

    assert config.settings["template_dirs"] == ["./templates/shop-theme/"]


def test_known_keys_are_resynced_as_attributes_after_load():
    mock_fs = Mock()
    mock_fs.read_file.return_value = """
    output_directory: ./dist
    template_engine: jinja2
    """

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))

    assert config.output_directory == "./dist"  # type: ignore
    assert config.template_engine == "jinja2"  # type: ignore


def test_unknown_keys_are_added_to_settings():
    mock_fs = Mock()
    mock_fs.read_file.return_value = """
    experimental_feature: true
    max_posts: 10
    """

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))

    assert config.settings["experimental_feature"] is True
    assert config.settings["max_posts"] == 10


def test_unknown_keys_are_added_as_attributes():
    mock_fs = Mock()
    mock_fs.read_file.return_value = "foo: bar"

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))

    # Everything in settings should also be an attribute
    assert config.foo == "bar"  # type: ignore
    assert "foo" in config.get_keys()


def test_get_existing_key():
    config = Config()
    assert config.get("source_directory") == "./source"


def test_get_missing_key_returns_default():
    config = Config()
    assert config.get("does_not_exist", "fallback") == "fallback"


def test_get_missing_key_returns_none_if_no_default():
    config = Config()
    assert config.get("does_not_exist") is None


def test_set_adds_new_key():
    config = Config()
    config.set("new_key", 123)

    assert config.settings["new_key"] == 123


def test_set_overrides_existing_key():
    config = Config()
    config.set("output_directory", "./build")

    assert config.settings["output_directory"] == "./build"
    assert config.output_directory == "./build"  # type: ignore


def test_set_does_not_create_attribute_for_unknown_key():
    config = Config()
    config.set("random", "value")

    assert not hasattr(config, "random")


def test_get_keys_returns_all_keys():
    config = Config()
    keys = config.get_keys()

    assert "source_directory" in keys
    assert "output_directory" in keys
    assert "template_engine" in keys


def test_get_keys_includes_loaded_keys():
    mock_fs = Mock()
    mock_fs.read_file.return_value = "site_name: My Site"

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))

    assert "site_name" in config.get_keys()


def test_load_yaml_with_non_dict_root_is_ignored():
    mock_fs = Mock()
    mock_fs.read_file.return_value = "- just\n- a\n- list"

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))

    # Defaults remain untouched
    assert config.settings["template_engine"] == "django"


def test_load_missing_file_does_not_crash():
    mock_fs = Mock()
    mock_fs.read_file.side_effect = FileNotFoundError

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))

    assert config.settings["output_directory"] == "./output"


def test_load_invalid_yaml_does_not_crash():
    mock_fs = Mock()
    mock_fs.read_file.return_value = "::: invalid :::"

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))

    assert config.settings["template_engine"] == "django"


def test_real_world_config_structure():
    mock_fs = Mock()
    mock_fs.read_file.return_value = """
    site_name: artart222 Portfolio/Blog
    base_url: https://artart.dev
    asset_dirs:
      - ./source/assets
    plugins:
      - BlogIndexerPlugin
      - SpecialPagesPlugin
    log_level: 10
    """

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))

    assert config.get("site_name") == "artart222 Portfolio/Blog"
    assert config.get("base_url") == "https://artart.dev"
    assert config.get("asset_dirs") == ["./source/assets"]
    assert config.get("plugins") == ["BlogIndexerPlugin", "SpecialPagesPlugin"]
    assert config.get("log_level") == 10


def test_config_loads_collections():
    mock_fs = Mock()
    mock_fs.read_file.return_value = """
    collections:
      blog:
        path: ./source/blogs
        type: blog
    """

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))

    assert config.get("collections")["blog"]["type"] == "blog"


def test_config_loads_react_section():
    mock_fs = Mock()
    mock_fs.read_file.return_value = """
    react:
      enabled: true
      collection: shop
      app_dir: ./react-app
    """

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))

    assert config.get("react")["enabled"] is True
    assert config.get("react")["collection"] == "shop"
