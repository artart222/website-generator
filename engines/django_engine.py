from django.conf import settings
import django
from django.template import Context, Template

# mark_safe is for mixing processed markdown with django template
import django.utils.safestring

from .base_engine import TemplateEngine
from utils.fs_manager import FileSystemManager

# TODO: Clean this file.


class DjangoTemplateEngine(TemplateEngine):
    """A template engine that uses Django's template system for rendering HTML templates."""

    def __init__(self) -> None:
        # --- Crucial Setup for Standalone DTL Usage ---
        if not settings.configured:
            settings.configure(
                TEMPLATES=[
                    {
                        "BACKEND": "django.template.backends.django.DjangoTemplates",
                        "OPTIONS": {},
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
        template = self.load_template(template_name)
        context_obj = Context(context)
        rendered_html = template.render(context_obj)
        return rendered_html

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
            print("Couldn't find ", template_name)
            print("Using default template")

        return Template(template_file)
