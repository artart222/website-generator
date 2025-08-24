from django.conf import settings
import django
from django.template import Context, Template, loader, exceptions

# mark_safe is for mixing processed markdown with django template
import django.utils.safestring

import logging

from .base_engine import TemplateEngine
from core.config import Config
from utils.fs_manager import FileSystemManager


class DjangoTemplateEngine(TemplateEngine):
    """A template engine that uses Django's template system for rendering HTML templates."""

    def __init__(self, config: Config) -> None:
        """
        Initializes the DjangoTemplateEngine.

        Args:
            template_dirs: A list of directories where templates are located.
        """
        self.logger = logging.getLogger(__name__)
        self.template_dirs: list[str] = config.settings["templates_directory"]
        self.logger.debug("Configuring standalone Django template.")
        # --- Crucial Setup for Standalone DTL Usage ---
        if not settings.configured:
            settings.configure(
                TEMPLATES=[
                    {
                        "BACKEND": "django.template.backends.django.DjangoTemplates",
                        # Tell Django where to find templates
                        "DIRS": self.template_dirs,
                        "APP_DIRS": False,  # We don't have Django "apps"
                    }
                ]
            )
            django.setup()
        # --- End of Setup ---

    def render(self, template_name: str, context: dict) -> str:
        """
        Renders a template by name with the given context.

        Args:
            template_name (str): The name of the template file to render.
            context (dict): The context data to pass to the template.

        Returns:
            str: The rendered HTML as a string.

        """
        """Renders a template by name with the given context."""
        try:
            # Using Django's built-in function to find and load the template
            template = loader.get_template(template_name)
            return template.render(context)
        except exceptions.TemplateDoesNotExist as e:
            msg = f"Template '{template_name}' does not exist."
            self.logger.error(msg)
            raise exceptions.TemplateDoesNotExist(msg) from e
        except Exception as e:
            msg = f"An unexpected error occurred while rendering '{template_name}'"
            self.logger.error(msg)
            raise RuntimeError(msg) from e

    def render_from_string(self, template_string: str, context: dict) -> str:
        """
        Renders a template from a string with the given context.

        Args:
            template_string (str): The template content as a string.
            context (dict): The context data to pass to the template.

        Returns:
            str: The rendered HTML as a string.
        """
        template = Template(template_string)
        context_obj = Context(context)
        rendered_html = template.render(context_obj)
        return rendered_html

    # TODO: Maybe remove this?
    def load_template(self, template_name: str) -> Template:
        """
        Loads a template by name from the templates directory.

        Args:
            template_name (str): The name of the template file to load.

        Returns:
            Template: A Django Template object loaded with the template content.
        """

        fs_handler = FileSystemManager()
        templates = fs_handler.list_files("./templates", recursive=True)
        found = False
        # TODO: change that in future to something like default.html
        # Setting a default template for fallback
        template_file = fs_handler.read_file("./templates/blog-theme/post.html")
        for template in templates:
            # If template name found in template path
            if template_name in template:
                found = True
                template_file = fs_handler.read_file(template)

        if not found:
            self.logger.warning(f"Couldn't find {template_name}")
            self.logger.info("Using default template")

        return Template(template_file)
