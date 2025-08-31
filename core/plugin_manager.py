from .config import Config
from plugins.base_plugin import BasePlugin
from .site import Site

import os
import importlib

import inspect
from plugins.base_plugin import BasePlugin
import logging

# TODO: Clean this file.

class PluginManager:
    def __init__(self, config: Config, site: Site) -> None:
        self.logger = logging.getLogger(__name__)
        self.config: Config = config
        self.site = site
        self.plugins: list[BasePlugin] = []

    def detect_and_load_plugins(self):
        plugins_list = self.config.get("plugins")
        # TODO: Check for possibilty of not correct plugins_list

        plugin_dir = "plugins"
        plugin_files = [
            f
            for f in os.listdir(plugin_dir)
            if f.endswith(".py") and f != "__init__.py"
        ]

        plugin_modules = []
        for filename in plugin_files:
            module_name = f"{plugin_dir}.{filename[:-3]}"  # Remove .py
            try:
                module = importlib.import_module(module_name)
                plugin_modules.append(module)
            except ImportError as e:
                print(f"Failed to import module {module_name}: {e}")

        plugins_to_load = []
        for module in plugin_modules:
            for name, obj in inspect.getmembers(module):
                # Check if it's a class
                if inspect.isclass(obj):
                    # Check if it inherits from BasePlugin and isn't the base class itself
                    if issubclass(obj, BasePlugin) and obj is not BasePlugin:
                        if obj.__name__ in plugins_list:
                            plugins_to_load.append(obj())

        self.plugins = plugins_to_load

    # def run_on_after_builds(self):
    #     for plugin in self.plugins:
    #         plugin.on_after_build(self.site)

    # def run_on_before_build(self):
    #     for plugin in self.plugins:
    #         plugin.on_before_build(self.site)

    def run_hook(self, hook_name: str, *args, **kwargs):
        """Runs a specified hook on all loaded plugins."""
        for plugin in self.plugins:
            method = getattr(plugin, hook_name, None)
            if method and callable(method):
                try:
                    method(*args, **kwargs)
                except Exception as e:
                    logging.error(
                        f"Plugin '{plugin.__class__.__name__}' failed on hook '{hook_name}': {e}"
                    )
