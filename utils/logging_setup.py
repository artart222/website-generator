import logging


def setup_logging(log_level: int) -> None:
    """
    Removes old handlers and sets up a new, configured root logger.

    Args:
        log_level: The logging level to set (e.g., logging.INFO).
    """

    root_logger = logging.getLogger()

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create new console handler
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root_logger.addHandler(handler)

    # Apply log level
    root_logger.setLevel(log_level)

    # Confirmation logs
    root_logger.info("Logger reconfigured successfully.")
    root_logger.info(f"Log level set to {logging.getLevelName(log_level)}")
