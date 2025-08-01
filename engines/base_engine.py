from abc import ABC, abstractmethod

class TemplateEngine(ABC):
    # TODO: Write doc strings for this
    @abstractmethod
    def render(self, template_name: str, context: dict) -> str:
        pass

    @abstractmethod
    def render_from_string(self, template_string: str, context: dict) -> str:
        pass