from utils.logging_setup import setup_logging
from core.project import Project
import logging


# Default log level(Info).
log_level = 10


def main():
    # Setup logging
    # TODO: Check this: maybe it's better to move it at the first of file
    # Outside the main function, after imports
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.info(
        "A basic logger has been added so "
        "the config.py file and utils.py could have a proper logging"
    )
    my_project = Project("config.yaml")
    user_log_level = my_project.config.get("log_level", 10)
    setup_logging(user_log_level)
    my_project.build()


if __name__ == "__main__":
    main()
