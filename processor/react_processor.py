import logging
import os
import shutil
import subprocess
from pathlib import Path

from core.config import Config
from utils.fs_manager import FileSystemManager

logger = logging.getLogger(__name__)


def build_react_section(
    config: Config,
    fs_manager: FileSystemManager,
    log: logging.Logger | None = None,
) -> None:
    """
    Builds the optional React/Next.js section and copies the static export.

    Args:
        config: The project configuration object.
        fs_manager: File system helper for copying directories.
        log: Optional logger override (defaults to module logger).
    """
    log = log or logger

    react_cfg = config.get("react", {})
    if not isinstance(react_cfg, dict) or not react_cfg.get("enabled", False):
        return

    collection = react_cfg.get("collection")
    if not collection:
        log.error("React build is enabled but no collection is set.")
        return

    app_dir = Path(react_cfg.get("app_dir", "./react-app"))
    if not app_dir.exists():
        log.error("React app directory not found: %s", app_dir)
        return

    export_subdir = react_cfg.get("export_subdir") or collection
    export_subdir = export_subdir.strip("/\\")
    base_path = react_cfg.get("base_path") or f"/{export_subdir}"
    if base_path and not str(base_path).startswith("/"):
        base_path = f"/{base_path}"
    asset_prefix = react_cfg.get("asset_prefix") or base_path
    if asset_prefix and not str(asset_prefix).startswith("/"):
        asset_prefix = f"/{asset_prefix}"

    frontend = config.get("frontend", {})
    export_data = frontend.get("export_data", {}) if isinstance(frontend, dict) else {}
    if not export_data.get("enabled", False):
        log.error("React build requires frontend.export_data.enabled = true.")
        return

    data_dir = Path(export_data.get("output_dir", "./output/data"))
    if not data_dir.exists():
        log.error(
            "React build requires JSON data at %s. Enable frontend.export_data and run build.",
            data_dir,
        )
        return

    public_data_dir = app_dir / "public" / "data"
    if public_data_dir.exists():
        shutil.rmtree(public_data_dir)
    fs_manager.copy_directory(data_dir, public_data_dir, exist_ok=True)

    env = os.environ.copy()
    env["NEXT_PUBLIC_BASE_PATH"] = base_path
    env["NEXT_PUBLIC_ASSET_PREFIX"] = asset_prefix
    env["NEXT_PUBLIC_COLLECTION"] = collection
    env["NEXT_PUBLIC_DATA_URL"] = "/data"

    try:
        npm = shutil.which("npm")
        if npm is None:
            raise RuntimeError("npm not found. Please install Node.js.")
        subprocess.run(
            [npm, "run", "build"],
            cwd=str(app_dir),
            env=env,
            check=True,
        )
    except FileNotFoundError as exc:
        log.error("npm not found; React build skipped.", exc_info=True)
        raise RuntimeError("npm not found on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        log.error("React build failed.", exc_info=True)
        raise RuntimeError("React build failed.") from exc

    export_dir = app_dir / "out"
    if not export_dir.exists():
        log.error("React export directory not found: %s", export_dir)
        return

    output_dir = Path(config.get("output_directory"))
    dest_dir = output_dir / export_subdir
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    fs_manager.copy_directory(export_dir, dest_dir, exist_ok=True)
