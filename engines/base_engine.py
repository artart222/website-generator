from abc import ABC, abstractmethod
from django.template import Template


class TemplateEngine(ABC):
    """
    Abstract base class for template engines.
    Defines the interface for rendering templates and loading them.
    """

    @abstractmethod
    def render(self, template_name: str, context: dict) -> str:
        """
        Render a template by name with the given context.

        Args:
            template_name (str): The name of the template to render.
            context (dict): The context data to use for rendering.

        Returns:
            str: The rendered template as a string.
        """
        pass

    @abstractmethod
    def render_from_string(self, template_string: str, context: dict) -> str:
        """
        Render a template from a string with the given context.

        Args:
            template_string (str): The template content as a string.
            context (dict): The context data to use for rendering.

        Returns:
            str: The rendered template as a string.
        """
        pass

    @abstractmethod
    def load_template(self, template_name: str) -> Template | str:
        """
        Load a template by name.

        Args:
            template_name (str): The name of the template to load.

        Returns:
            Template | str: The loaded template object or its content as a string.
        """
        pass
