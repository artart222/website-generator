from .base_plugin import BasePlugin


class TestPluginA(BasePlugin):
    def inject_css(self, **kwargs):
        return ["/a.css"]

    def modify_template_context(self, **kwargs):
        return {"order": "a"}
