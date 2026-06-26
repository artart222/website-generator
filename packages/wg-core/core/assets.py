"""Output-directory preparation and asset copying.

Extracted (behavior-preserving) from the former ``Project`` god class.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from .build_context import BuildContext
from .errors import BuildError


class OutputPreparer:
    """Creates and clears the output directory safely before a build."""

    def __init__(self, ctx: BuildContext) -> None:
        self.ctx = ctx

    def prepare(self) -> None:
        output_dir = Path(self.ctx.config.get("build.output_directory"))
        resolved_output_dir = output_dir.resolve()
        project_root = Path.cwd().resolve()

        if resolved_output_dir == project_root:
            raise BuildError(
                f"Refusing to use the project root as the output directory: {resolved_output_dir}"
            )
        if output_dir.exists() and output_dir.is_file():
            raise BuildError(f"Output path is a file, not a directory: {output_dir}")

        self.ctx.fs_manager.create_directory(output_dir)

        # Incremental builds reuse unchanged output, so the directory is kept.
        if self.ctx.incremental:
            return

        for child in output_dir.iterdir():
            if child.name == ".git":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()


class AssetCopier:
    """Copies theme, extension, and configured asset directories into output."""

    def __init__(self, ctx: BuildContext) -> None:
        self.ctx = ctx
        self.logger = logging.getLogger(__name__)

    def copy(self) -> None:
        ctx = self.ctx
        output_dir = Path(ctx.config.get("build.output_directory"))
        ctx.theme_manager.prepare_theme_output(output_dir)
        ctx.extension_manager.copy_extension_assets(output_dir)

        asset_dirs = list(ctx.config.get("build.asset_dirs", []))
        if "./styles" not in asset_dirs:
            asset_dirs.insert(0, "./styles")

        for asset_dir_value in asset_dirs:
            asset_dir = Path(asset_dir_value)
            if asset_dir.exists():
                ctx.fs_manager.copy_directory(
                    asset_dir, output_dir / asset_dir.name, exist_ok=True
                )
                self.logger.info("Copied asset directory: %s", asset_dir)
            else:
                self.logger.warning("Asset directory does not exist: %s", asset_dir)
