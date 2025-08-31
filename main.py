from utils.logging_setup import setup_logging
from core.project import Project
import logging

# --- minimal bootstrap logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Default log level (DEBUG)
DEFAULT_LOG_LEVEL = logging.DEBUG


def main() -> None:
    """
    Entry point for the static site generator script.

    Sets up logging, loads the project configuration, and builds the site.
    """
    logger.info("Starting project build process...")

    try:
        my_project = Project("config.yaml")
    except Exception as e:
        logger.error(f"Failed to initialize project: {e}")
        return

    user_log_level = my_project.config.get("log_level", DEFAULT_LOG_LEVEL)
    setup_logging(user_log_level)

    try:
        my_project.build()
        logger.info("Project build completed successfully.")
    except Exception as e:
        logger.error(f"Project build failed: {e}")


if __name__ == "__main__":
    main()
