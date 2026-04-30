from pathlib import Path
import logging
import shutil
import subprocess
import sys
from urllib.parse import urlparse

from core.bootstrap import bootstrap
from core.config import Config
from utils.fs_manager import FileSystemManager

logger = logging.getLogger(__name__)


def clean(config: Config, fs: FileSystemManager) -> None:
    output_path = Path(config.get("output_directory"))
    if fs.path_exists(output_path):
        logger.info("Cleaning output directory...")
        shutil.rmtree(output_path)
        logger.info("Output directory cleaned.")


def build() -> None:
    logger.info("Generating site...")
    subprocess.run([sys.executable, "main.py"], check=True)
    logger.info("Site generated.")


def start_runtime(config: Config) -> subprocess.Popen | None:
    runtime_targets = config.get("runtime.targets", [])
    if not isinstance(runtime_targets, list) or not runtime_targets:
        return None

    runtime_target = runtime_targets[0]
    if not isinstance(runtime_target, dict):
        return None

    public_base_url = str(runtime_target.get("public_base_url", "")).strip()
    parsed = urlparse(public_base_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8787
    runtime_type = str(runtime_target.get("type", "mock_runtime")).strip()

    if runtime_type == "django_service":
        # runtime_entrypoint = Path(__file__).resolve().parent / "wg_runtime" / "manage.py"
        runtime_entrypoint  = "wg_runtime.manage"
        logger.info("Starting Django runtime at http://%s:%s", host, port)
        return subprocess.Popen(
            [sys.executable, "-m", str(runtime_entrypoint), "runserver", f"{host}:{port}"],
        )

    logger.info("Starting mock runtime at http://%s:%s", host, port)
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "cli",
            "runtime",
            "mock",
            "--config",
            "config.yaml",
            "--host",
            host,
            "--port",
            str(port),
        ]
    )


def serve(config: Config) -> None:
    logger.info("Serving site at http://localhost:8000")
    subprocess.run(
        [sys.executable, "-m", "http.server", "8000"],
        cwd=config.get("output_directory"),
        check=True,
    )


if __name__ == "__main__":
    config = bootstrap("config.yaml")
    fs_manager = FileSystemManager()

    clean(config, fs_manager)
    build()
    runtime_process = start_runtime(config)
    try:
        serve(config)
    finally:
        if runtime_process is not None:
            runtime_process.terminate()
