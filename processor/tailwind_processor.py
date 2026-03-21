import logging
import subprocess
from pathlib import Path
import shutil


from core.config import Config

logger = logging.getLogger(__name__)


def build_tailwind(config: Config) -> None:
    """
    Runs the Tailwind CLI build using the project's configuration.

    Args:
        config: The project configuration object.
    """
    tailwind = config.get(
        "experimental.tailwind",
        config.get("frontend", {}).get("tailwind", {}),
    )
    if not isinstance(tailwind, dict) or not tailwind.get("enabled", False):
        logger.info("Tailwind build is disabled.")
        return

    input_path = Path(tailwind.get("input", "./styles/tailwind.input.css"))
    output_path = Path(tailwind.get("output", "./styles/tailwind.css"))
    config_path = Path(tailwind.get("config", "./tailwind.config.js"))
    minify = bool(tailwind.get("minify", False))

    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)

    npx = shutil.which("npx")

    if npx is None:
        raise RuntimeError("npx not found. Please install Node.js.")

    args = [
        npx,
        "tailwindcss",
        "-c",
        str(config_path),
        "-i",
        str(input_path),
        "-o",
        str(output_path),
    ]
    if minify:
        args.append("--minify")

    logger.info("Running Tailwind build: %s", " ".join(args))
    try:
        subprocess.run(args, check=True)
        logger.info("Tailwind build completed successfully.")
    except FileNotFoundError as exc:
        msg = "Tailwind build failed: 'npx' was not found on PATH."
        logger.error(msg)
        raise RuntimeError(msg) from exc
    except subprocess.CalledProcessError as exc:
        msg = "Tailwind build failed. Check Tailwind configuration and inputs."
        logger.error(msg)
        raise RuntimeError(msg) from exc
