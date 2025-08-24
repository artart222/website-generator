from .django_engine import DjangoTemplateEngine
from .base_engine import TemplateEngine
from core.config import Config
import logging


TEMPLATE_ENGINES = {
    "django": DjangoTemplateEngine,
}


def create_template_engine(name: str, config: Config) -> TemplateEngine:
    """
    Looks up and returns an instance of the requested template engine.

    Args:
        name: The name of engine.

    Returns:
        The instance of TemplateEngine class
    Raises:
        ValueError: If no template engine is found for the given name.
    """
    logging.info(f"Attempting to use '{name}' as template engine.")
    engine_class = TEMPLATE_ENGINES.get(name)
    if not engine_class:
        logging.warning(f"Unknown template engine: '{name}'.")
        raise ValueError(f"Unknown template engine: '{name}'")
    logging.info(f"Successfully created '{name}' template engine.")
    return engine_class(config)
