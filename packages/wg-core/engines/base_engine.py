from abc import ABC, abstractmethod


class TemplateEngine(ABC):
    """Abstract interface for template engines.

    Intentionally narrow: the build only needs to render a named template or a
    template string. The previous ``load_template`` method was unused and forced
    one implementation to raise ``NotImplementedError`` (an LSP/ISP violation),
    so it has been removed. This abstraction also no longer imports any concrete
    engine (e.g. Django) - infrastructure depends on the abstraction, not the
    reverse.
    """

    @abstractmethod
    def render(self, template_name: str, context: dict) -> str:
        """Render a template by name with the given context."""

    @abstractmethod
    def render_from_string(self, template_string: str, context: dict) -> str:
        """Render a template provided as a string with the given context."""
