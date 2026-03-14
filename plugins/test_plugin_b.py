from .base_plugin import BasePlugin


class TestPluginB(BasePlugin):
    def inject_css(self, **kwargs):
        return ["/b.css"]

    def modify_template_context(self, **kwargs):
        return {"order": "b"}
