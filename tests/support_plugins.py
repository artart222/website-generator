from plugins.base_plugin import BasePlugin


class TestPluginA(BasePlugin):
    __test__ = False

    def inject_css(self, **kwargs):
        return ["/a.css"]

    def modify_template_context(self, **kwargs):
        return {"order": "a"}


class TestPluginB(BasePlugin):
    __test__ = False

    def inject_css(self, **kwargs):
        return ["/b.css"]

    def modify_template_context(self, **kwargs):
        return {"order": "b"}
