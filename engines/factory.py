from .django_engine import DjangoTemplateEngine
from .base_engine import TemplateEngine
import logging


TEMPLATE_ENGINES = {
    "django": DjangoTemplateEngine,
}


def create_template_engine(
    name: str, template_dirs: list[str]
) -> TemplateEngine:
    """
    Looks up and returns an instance of the requested template engine.

    Args:
        name: The name of the engine.
        template_dirs: A list of directories where templates are located.

    Returns:
        An initialized instance of a TemplateEngine class.
        
    Raises:
        ValueError: If no template engine is found for the given name.
    """
    logging.info(f"Attempting to create '{name}' template engine.")
    engine_class = TEMPLATE_ENGINES.get(name)
    
    if not engine_class:
        msg = f"Unknown template engine: '{name}'"
        logging.error(msg)
        raise ValueError(msg)
        
    logging.info(f"Successfully created '{name}' template engine.")
    return engine_class(template_dirs)