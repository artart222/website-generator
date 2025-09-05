import os
import sys


# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # Go up one level from tests/
sys.path.insert(0, project_root)

from unittest.mock import Mock
from core.config import Config


def test_config_initialization_with_defaults():
    """Test that Config initializes with correct default values."""
    # Act
    config = Config()

    # Assert
    assert config.settings["source_directory"] == "./source"
    assert config.settings["output_directory"] == "./output"
    assert config.settings["template_engine"] == "django"


def test_config_load_from_file():
    """Test loading configuration from a YAML file."""
    # Arrange
    mock_fs_manager = Mock()
    config_data = {"site_name": "Test Site", "output_directory": "./build"}

    # Mock the read_file method to return YAML content
    mock_fs_manager.read_file.return_value = """
    site_name: Test Site
    output_directory: ./build
    """

    config = Config(fs_manager=mock_fs_manager)

    # Act
    config.load("config.yaml")

    # Assert
    assert config.settings["site_name"] == "Test Site"
    assert config.settings["output_directory"] == "./build"
    mock_fs_manager.read_file.assert_called_once_with("config.yaml")


def test_config_get_and_set_methods():
    """Test getting and setting configuration values."""
    # Arrange
    config = Config()

    # Act - Test get method
    source_dir = config.get("source_directory")

    # Assert
    assert source_dir == "./source"

    # Act - Test set method
    config.set("new_setting", "new_value")

    # Assert
    assert config.get("new_setting") == "new_value"
    assert config.settings["new_setting"] == "new_value"
