from __future__ import annotations

import logging

from django.template import Context, Engine, Template, exceptions
from typing import NoReturn

from .base_engine import TemplateEngine


class DjangoTemplateEngine(TemplateEngine):
    """Standalone Django template engine used without a full Django app."""

    def __init__(self, template_dirs: list[str]) -> None:
        self.logger = logging.getLogger(__name__)
        self.template_dirs = template_dirs
        self.engine = Engine(
            dirs=self.template_dirs,
            app_dirs=False,
            debug=False,
        )

    def render(self, template_name: str, context: dict) -> str:
        try:
            template = self.engine.get_template(template_name)
            return template.render(Context(context))
        except exceptions.TemplateDoesNotExist as exc:
            msg = f"Template '{template_name}' does not exist."
            self.logger.error(msg)
            raise exceptions.TemplateDoesNotExist(msg) from exc
        except Exception as exc:
            msg = f"An unexpected error occurred while rendering '{template_name}'"
            self.logger.error(msg)
            raise RuntimeError(msg) from exc

    def render_from_string(self, template_string: str, context: dict) -> str:
        template = Template(template_string, engine=self.engine)
        return template.render(Context(context))

    def load_template(self, template_name: str) -> NoReturn:
        raise NotImplementedError(
            "load_template() is not supported for DjangoTemplateEngine. Use render() instead."
        )
