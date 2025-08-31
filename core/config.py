import yaml
import logging
from typing import Any, Optional, Dict
from utils.fs_manager import FileSystemManager


class Config:
    """
    Loads, stores, and provides access to project settings
    from a configuration file (YAML).

    Supports default known keys as attributes,
    but also allows arbitrary extra keys.
    """

    def __init__(
        self,
        fs_manager: Optional[FileSystemManager] = None,
    ) -> None:
        """
        Initializes the configuration manager with default settings.

        Args:
            fs_manager (FileSystemManager, optional): Custom file system manager. Defaults to a new FileSystemManager instance.
        """
        self.logger = logging.getLogger(__name__)
        self.fs_manager = fs_manager or FileSystemManager()

        # Defaults for known keys as attributes.
        self.settings: Dict[str, Any] = {
            "source_directory": "./source",
            "output_directory": "./output",
            # TODO: Add default.html template
            "template_dirs": ["./templates/blog-template/"],
            "template_engine": "django",
        }

        # Sync attributes for known keys for easy access
        self._sync_attributes_from_settings()

    def _sync_attributes_from_settings(self):
        """
        Sync known keys from the settings dict to instance attributes.
        """
        for key in self.settings:
            setattr(self, key, self.settings[key])

    def load(self, filepath: str = "./config.yaml") -> None:
        """
        Loads configuration from a YAML file and updates settings.

        Overrides defaults if keys exist in file,
        adds any unknown keys as well.

        Args:
            filepath: Path to the YAML config file.

        Raises:
            FileNotFoundError: If the file does not exist.
            yaml.YAMLError: If YAML parsing fails.
        """
        self.logger.debug(f"Loading config from '{filepath}'")
        try:
            file_content = self.fs_manager.read_file(filepath)
            loaded_settings: Optional[dict[str, Any]] = (
                yaml.safe_load(file_content) or {}
            )

            if not isinstance(loaded_settings, dict):
                raise yaml.YAMLError("Config root element must be a dictionary")

            # Update settings dict with loaded keys (overrides defaults if keys overlap)
            self.settings.update(loaded_settings)

            # Sync known keys as attributes again to reflect overrides
            self._sync_attributes_from_settings()

            self.logger.info(
                f"Config loaded from '{filepath}' with keys: {list(self.settings.keys())}"
            )

        except FileNotFoundError:
            self.logger.error(f"Config file not found: {filepath}")
            self.logger.warning("Using default settings")
        except yaml.YAMLError:
            self.logger.error(f"YAML parsing error in config file '{filepath}'")
            self.logger.warning("Using default settings")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration setting by key.

        Args:
            key: The configuration key.
            default: Value to return if key not found.

        Returns:
            The setting value or default.
        """
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Sets or updates a configuration setting.

        Updates attribute if it's one of the known default keys.

        Args:
            key: The configuration key to set.
            value: The value to assign.
        """
        self.settings[key] = value
        if hasattr(self, key):
            setattr(self, key, value)
        self.logger.debug(f"Config setting updated: {key} = {value}")

    def get_keys(self) -> list[str]:
        """
        Returns all configuration keys currently stored.

        Returns:
            List of all configuration keys.
        """
        return list(self.settings.keys())
