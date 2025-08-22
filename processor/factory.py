import logging
from .base_processor import ContentProcessor
from .markdown_processor import MarkdownProcessor

PROCESSOR_MAP = {"md": MarkdownProcessor(["extra", "meta", "codehilite"])}


def create_content_processor(name: str) -> ContentProcessor:
    """
    Looks up and returns an instance of the requested content processor.

    Args:
        name: The name of the processor (e.g. "md", "txt").

    Returns:
        An initialized instance of the content processor.
    """
    logging.debug(f"Attempting to create content processor for '{name}'.")
    processor_class = PROCESSOR_MAP.get(
        name.lower()
    )  # Use .lower() for case-insensitivity

    # TODO: Complete this in future.
    if not processor_class:
        # logging.warning(f"No content processor found for '{name}'. Defaulting to PlainTextProcessor.")
        # Defaulting to a plain text processor is a safe fallback.
        # return PlainTextProcessor()
        logging.error(f"No content processor found for '{name}'.")
        raise

    logging.info(f"Successfully created '{name}' content processor.")
    return processor_class
