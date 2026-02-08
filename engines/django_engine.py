from django.conf import settings
import django
from django.template import Context, Template, loader, exceptions

# mark_safe is for mixing processed markdown with django template
import django.utils.safestring

import logging

from typing import NoReturn

from .base_engine import TemplateEngine
from utils.fs_manager import FileSystemManager


class DjangoTemplateEngine(TemplateEngine):
    """A template engine that uses Django's template system for rendering HTML templates."""

    def __init__(self, template_dirs: list[str]) -> None:
        """
        Initializes the DjangoTemplateEngine.

        Args:
            template_dirs: A list of directories where templates are located.
        """
        self.logger = logging.getLogger(__name__)
        self.templates_dirs = template_dirs
        self.fs_manager = FileSystemManager()
        self.logger.debug("Configuring standalone Django template.")
        # --- Crucial Setup for Standalone DTL Usage ---
        if not settings.configured:
            settings.configure(
                TEMPLATES=[
                    {
                        "BACKEND": "django.template.backends.django.DjangoTemplates",
                        # Tell Django where to find templates
                        "DIRS": self.templates_dirs,
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
            template_name: The name of the template file to render.
            context: The context data to pass to the template.

        Returns:
            The rendered HTML as a string.

        Raises:
            django.template.exceptions.TemplateDoesNotExist: If the template does not exist.
            RuntimeError: For other errors.
        """
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
            template_string: The template content as a string.
            context: The context data to pass to the template.

        Returns:
            The rendered HTML as a string.
        """
        template = Template(template_string)
        context_obj = Context(context)
        rendered_html = template.render(context_obj)
        return rendered_html

    # TODO: Maybe remove this?
    # def load_template(self, template_name: str) -> Template:
    #     """
    #     Loads a template by name from the templates directory.

    #     Args:
    #         template_name: The name of the template file to load.

    #     Returns:
    #         A Django Template object loaded with the template content.
    #     """

    #     templates = []
    #     for dir_path in self.templates_dirs:
    #         templates.extend(self.fs_manager.list_files(dir_path, recursive=True))
    #     found = False
    #     # TODO: change that in future to something like default.html
    #     # Setting a default template for fallback
    #     # TODO: Change this in future
    #     template_file = self.fs_manager.read_file("./templates/blog-template/post.html")
    #     for template in templates:
    #         # If template name found in template path
    #         if template_name in template:
    #             found = True
    #             template_file = self.fs_manager.read_file(template)

    #     if not found:
    #         self.logger.warning(f"Couldn't find {template_name}")
    #         self.logger.info("Using default template")

    #     self.logger.debug(f"Template name: '{template_name}'")
    #     self.logger.debug(f"Template file path: '{template_file}'")

    #     return Template(template_file)

    def load_template(self, template_name: str) -> NoReturn:
        """
        NOT SUPPORTED.

        DjangoTemplateEngine does not expose template loading.
        Templates are loaded internally by Django via loader.get_template().
        """
        raise NotImplementedError(
            "load_template() is not supported for DjangoTemplateEngine. "
            "Use render() instead."
        )
