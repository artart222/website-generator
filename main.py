import logging
from core.bootstrap import bootstrap
from core.project import Project

logger = logging.getLogger(__name__)


def main() -> None:
    config = bootstrap("config.yaml")

    logger.info("Starting project build process...")
    project = Project(config)
    project.build()
    logger.info("Project build completed successfully.")


if __name__ == "__main__":
    main()
