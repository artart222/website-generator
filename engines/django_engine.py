from django.conf import settings
import django
from django.template import Context, Template

# mark_safe is for mixixng proccessed markdown with django template
import django.utils.safestring

from .base_engine import TemplateEngine

# TODO: Clean this file.
# TODO: Add doc string.


class DjangoTemplateEngine(TemplateEngine):
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
        template = Template(template_name)
        context_obj = Context(context)
        rendered_html = template.render(context_obj)
        return rendered_html

    def render_from_string(self, template_string: str, context: dict) -> str:
        template = Template(template_string)
        context_obj = Context(context)
        rendered_html = template.render(context_obj)
        return rendered_html
