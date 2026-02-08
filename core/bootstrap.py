from pathlib import Path
import logging

from utils.logging_setup import setup_logging

# from .core.config import load_config
from .config import Config

logger = logging.getLogger(__name__)

DEFAULT_LOG_LEVEL = 10


def bootstrap(config_path: str | Path) -> Config:
    """
    Bootstrap the application environment.

    Responsibilities:
    - Initialize logging early
    - Load configuration

    This function MUST be called by all executable entrypoints
    (e.g. main.py, dev.py).

    Args:
        config_path: Path to the configuration file.

    Returns:
        Loaded configuration object.

    Raises:
        FileNotFoundError: If config file does not exist.
        Exception: For invalid configuration.
    """

    # --- minimal early logging (safe default) ---
    setup_logging(logging.INFO)
    logger.debug("Bootstrap started.")

    config_path = Path(config_path).resolve()

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # --- load config ---
    config = Config()
    config.load(str(config_path))

    # --- reconfigure logging using config ---
    log_level = config.get("log_level", DEFAULT_LOG_LEVEL)
    setup_logging(log_level)

    logger.debug("Logging configured with level: %s", log_level)
    logger.debug("Configuration loaded successfully.")

    return config
