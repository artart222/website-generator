from abc import ABC, abstractmethod
from django.template import Template


class TemplateEngine(ABC):
    # TODO: Write doc strings for this
    @abstractmethod
    def render(self, template_name: str, context: dict) -> str:
        pass

    @abstractmethod
    def render_from_string(self, template_string: str, context: dict) -> str:
        pass

    @abstractmethod
    def load_template(self, template_name: str) -> Template | str:
        pass
