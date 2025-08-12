"""
Configuration

Responsibility: Loads, stores, and provides access to project settings from a configuration file (e.g., YAML, JSON, TOML).
Attributes:
settings: dict - Internal dictionary holding all configuration data.
source_directory: str - Path to content and template sources.
output_directory: str - Path where the generated site will be saved.
templates_directory: str - Path to template files within the source directory.
assets_directory: str - Path to static assets within the source directory.
pages_directory: str - Path to page content files.
default_template: str - Default template to use if a page doesn't specify one.
plugins: list[dict] - Configuration for plugins to be loaded.
Methods:
load(filepath: str): Loads configuration from the given file.
get(key: str, default: Any = None) -> Any: Retrieves a setting.
set(key: str, value: Any): Sets a setting (primarily for internal/plugin use).
"""

import yaml
from typing import Any
from utils.fs_manager import FileSystemManager


class Config:
    def __init__(self) -> None:
        self.settings: dict = {}
        self.source_directory: str
        self.output_directory: str
        self.templates_directory: str
        self.debug: bool = True
        # assets_directory: str
        # pages_directory: str
        # default_template: str
        # plugins: list[dict]
        pass

    def load(self, filepath: str = "./config.yaml"):
        # TODO: Write docstrings
        # TODO: Error proof this
        fs_manager = FileSystemManager()
        setting_file = fs_manager.read_file(filepath)
        # For preventing setting self.settings to None
        self.settings = yaml.safe_load(setting_file) or {}
        for k, v in self.settings.items():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                print(f"[Config] Ignored unknown setting: {k}")

    def get(self, key: Any = None, default: Any = None):
        return self.settings.get(key, default)

    def set(self, key: str, value: Any):
        self.settings[key] = value
