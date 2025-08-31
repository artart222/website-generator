import logging
from .base_processor import ContentProcessor
from .markdown_processor import MarkdownProcessor

# This dictionary maps identifiers to the processor CLASS.
# The factory will create the instances
_PROCESSOR_MAP = {"md": MarkdownProcessor}

# Central place to manage default settings for processors
_DEFAULT_EXTENSIONS = {"md": ["extra", "meta", "codehilite"]}


def create_content_processor(name: str) -> ContentProcessor:
    """
    Looks up and returns an instance of the requested content processor.

    Args:
        name: The name of the processor (e.g., "md").

    Returns:
        An initialized instance of the content processor.

    Raises:
        ValueError: If no processor is found for the given name.
        RuntimeError: If the processor class fails to initialize.
    """
    logging.debug(f"Attempting to create content processor for '{name}'.")
    processor_class = _PROCESSOR_MAP.get(
        name.lower()
    )  # Use .lower() for case-insensitivity
    if not processor_class:
        msg = f"No content processor found for '{name}'."
        logging.error(msg)
        raise ValueError(msg)
    try:
        # Check if there are default extensions for this processor type
        extensions = _DEFAULT_EXTENSIONS.get(name.lower())
        if extensions:
            instance = processor_class(extensions=extensions)
        else:
            instance = processor_class()
        logging.info(f"Successfully created '{name}' content processor.")
        return instance
    except Exception as e:
        # Catch any error during instantiation and wrap it.
        msg = f"Failed to create an instance of the content processor for '{name}'."
        logging.error(msg)
        raise RuntimeError(msg) from e
