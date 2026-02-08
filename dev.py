import shutil
import subprocess
import sys
import logging

from core.bootstrap import bootstrap
from utils.fs_manager import FileSystemManager
from core.config import Config

logger = logging.getLogger(__name__)


def clean(config: Config, fs: FileSystemManager) -> None:
    if fs.path_exists(config.get("output_directory")):
        logger.info("🧹 Cleaning output directory...")
        shutil.rmtree(config.get("output_directory"))
        logger.info("🧹 Output directory cleaned.")


def build() -> None:
    logger.info("🏗️  Generating site...")
    subprocess.run([sys.executable, "main.py"], check=True)
    logger.info("🏗️  Site generated.")


def serve(config: Config) -> None:
    logger.info("🚀 Serving site at http://localhost:8000")
    subprocess.run(
        [sys.executable, "-m", "http.server", "8000"],
        cwd=config.get("output_directory"),
        check=True,
    )


if __name__ == "__main__":
    config = bootstrap("config.yaml")
    # config.load("config.yaml")
    fs_manager = FileSystemManager()

    clean(config, fs_manager)
    build()
    serve(config)
