from .config import Config
from plugins.base_plugin import BasePlugin
from .site import Site

import importlib
import inspect
import logging
from pathlib import Path


class PluginManager:
    """
    Manages the discovery, loading, and execution of plugins.

    A plugin is a class that inherits from `BasePlugin`, located in the `plugins/`
    directory, and explicitly listed in the `plugins` section of the config.
    """

    def __init__(self, config: Config, site: Site) -> None:
        """
        Initialize the plugin manager.

        Args:
            config (Config): Application configuration.
            site (Site): The site instance, representing the project being built.
        """
        self.logger = logging.getLogger(__name__)
        self.config: Config = config
        self.site: Site = site
        self.plugins: list[BasePlugin] = []

    def detect_and_load_plugins(self) -> list[BasePlugin]:
        """
        Detects available plugin modules in the `plugins/` directory,
        imports them dynamically, and loads classes that match the following criteria:
          - Subclass of `BasePlugin`
          - Class name is listed in the config under `plugins`

        Successfully matched plugins are instantiated and stored in `self.plugins`.

        Raises:
            ImportError: If a plugin module cannot be imported.
            Exception: If plugin instantiation fails.
        """
        plugins_list = self.config.get("plugins", [])
        if not isinstance(plugins_list, list):
            self.logger.warning("'plugins' should be a list in config. Skipping.")
            plugins_list = []
            return []

        plugin_package = importlib.import_module("plugins")
        plugin_dir = Path(plugin_package.__file__).resolve().parent
        plugin_files = [
            path.name
            for path in plugin_dir.iterdir()
            if path.suffix == ".py" and path.name != "__init__.py"
        ]

        plugin_modules = []
        for filename in plugin_files:
            module_name = f"{plugin_package.__name__}.{filename[:-3]}"
            try:
                module = importlib.import_module(module_name)
                plugin_modules.append(module)
            except ImportError as e:
                self.logger.error(
                    f"Failed to import module {module_name}: {e}", exc_info=True
                )

        discovered_plugins: dict[str, type[BasePlugin]] = {}
        for module in plugin_modules:
            for _, obj in inspect.getmembers(module):
                # Check if it's a class
                if inspect.isclass(obj):
                    # Check if it inherits from BasePlugin and isn't the base class itself
                    if issubclass(obj, BasePlugin) and obj is not BasePlugin:
                        discovered_plugins[obj.__name__] = obj

        plugins_to_load: list[BasePlugin] = []
        for plugin_name in plugins_list:
            plugin_class = discovered_plugins.get(plugin_name)
            if plugin_class:
                plugins_to_load.append(plugin_class())
            else:
                self.logger.warning(
                    f"Plugin '{plugin_name}' was listed in config but not found."
                )

        self.plugins = plugins_to_load
        return self.plugins

    def run_hook(self, hook_name: str, *args, **kwargs) -> None:
        """
        Executes a named hook method on all loaded plugins.

        For each plugin:
          - If the plugin defines a method with the given hook name,
            that method is called with the provided arguments.

        Args:
            hook_name: The name of the hook/method to call on plugins.
            *args: Positional arguments passed to the hook method.
            **kwargs: Keyword arguments passed to the hook method.

        Notes:
            - If a plugin raises an exception, it is logged but does not stop other plugins.
            - Errors include full stack traces in logs for debugging.
        """
        for plugin in self.plugins:
            method = getattr(plugin, hook_name, None)
            if method and callable(method):
                try:
                    method(*args, **kwargs)
                except Exception as e:
                    self.logger.error(
                        f"Plugin '{plugin.__class__.__name__}' failed on hook '{hook_name}': {e}",
                        exc_info=True,
                    )

    def run_hook_collect(self, hook_name: str, *args, **kwargs) -> list:
        """
        Executes a named hook method on all loaded plugins and collects results.

        Args:
            hook_name: The name of the hook/method to call on plugins.
            *args: Positional arguments passed to the hook method.
            **kwargs: Keyword arguments passed to the hook method.

        Returns:
            List of non-None results returned by plugins, in plugin order.
        """
        results: list = []
        for plugin in self.plugins:
            method = getattr(plugin, hook_name, None)
            if method and callable(method):
                try:
                    result = method(*args, **kwargs)
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    self.logger.error(
                        f"Plugin '{plugin.__class__.__name__}' failed on hook '{hook_name}': {e}",
                        exc_info=True,
                    )
        return results
