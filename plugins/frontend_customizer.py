from .base_plugin import BasePlugin
from core.config import Config


class FrontendCustomizer(BasePlugin):
    """
    Example frontend plugin that can inject CSS/JS and tweak template context.

    Expected optional config structure:
      frontend:
        customizer:
          body_class: "custom-body"
          container_class: "custom-container"
          extra_css:
            - "/styles/extra.css"
          extra_js:
            - "/scripts/extra.js"
    """

    def modify_template_context(self, **kwargs):
        config: Config = kwargs["config"]
        frontend = config.get("frontend", {})
        customizer = frontend.get("customizer", {}) if isinstance(frontend, dict) else {}

        updates = {}
        body_class = customizer.get("body_class")
        if body_class:
            updates["body_class"] = body_class

        container_class = customizer.get("container_class")
        if container_class:
            updates["container_class"] = container_class

        return updates or None

    def inject_css(self, **kwargs):
        config: Config = kwargs["config"]
        frontend = config.get("frontend", {})
        customizer = frontend.get("customizer", {}) if isinstance(frontend, dict) else {}
        extra_css = customizer.get("extra_css", [])
        return extra_css if extra_css else None

    def inject_js(self, **kwargs):
        config: Config = kwargs["config"]
        frontend = config.get("frontend", {})
        customizer = frontend.get("customizer", {}) if isinstance(frontend, dict) else {}
        extra_js = customizer.get("extra_js", [])
        return extra_js if extra_js else None
