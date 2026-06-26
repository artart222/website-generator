from typing import List, Optional
import shutil
import logging
from pathlib import Path


class FileSystemManager:
    """Filesystem operations behind a single, mockable seam.

    Centralizing IO here keeps the rest of the code testable (a fake
    implementing :class:`wg_contracts.ports.FileSystemPort` can be injected) and
    gives every operation consistent, contextual error messages.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def read_file(self, filepath: Path) -> str:
        """Read and return the text content of a file (UTF-8)."""
        self.logger.debug("Attempting to read file: %s", filepath)
        try:
            content = filepath.read_text(encoding="utf-8")
            self.logger.debug("Successfully read file: %s", filepath)
            return content
        except FileNotFoundError as exc:
            msg = f"File not found at path: {filepath}"
            self.logger.error(msg)
            raise FileNotFoundError(msg) from exc
        except PermissionError as exc:
            msg = f"Permission denied when reading file: {filepath}"
            self.logger.error(msg)
            raise PermissionError(msg) from exc
        except OSError as exc:
            msg = f"OS error occurred while reading file: {filepath}"
            self.logger.error(msg)
            raise IOError(msg) from exc

    def write_file(self, filepath: Path, content: str) -> None:
        """Write text content to a file, creating parent directories as needed."""
        self.logger.debug("Attempting to write file to: %s", filepath)
        try:
            filepath = filepath.resolve()
            if not filepath.parent.exists():
                self.logger.debug("Creating parent directories for: %s", filepath.parent)
                self.create_directory(filepath.parent)
            filepath.write_text(content, encoding="utf-8")
            self.logger.debug("Successfully wrote file: %s", filepath)
        except PermissionError as exc:
            msg = f"Permission denied when writing to file: {filepath}"
            self.logger.error(msg)
            raise PermissionError(msg) from exc
        except OSError as exc:
            msg = f"OS error occurred while writing file: {filepath}"
            self.logger.error(msg)
            raise IOError(msg) from exc

    def copy_file(self, source_path: Path, dest_path: Path) -> None:
        """Copy a single file, ensuring the destination directory exists."""
        self.logger.debug("Attempting to copy from '%s' to '%s'", source_path, dest_path)
        try:
            if source_path.resolve() == dest_path.resolve():
                msg = f"Source and destination are the same file: {source_path}."
                self.logger.warning(msg)
                raise shutil.SameFileError(msg)
            if not source_path.is_file():
                msg = f"Source file does not exist: {source_path}"
                self.logger.error(msg)
                raise FileNotFoundError(msg)
            if not dest_path.parent.exists():
                dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, dest_path)
            self.logger.debug("Successfully copied '%s' to '%s'", source_path, dest_path)
        except FileNotFoundError as exc:
            msg = f"Source file for copy not found: {source_path}"
            self.logger.error(msg)
            raise FileNotFoundError(msg) from exc
        except PermissionError as exc:
            msg = f"Permission denied during copy from '{source_path}' to '{dest_path}'"
            self.logger.error(msg)
            raise PermissionError(msg) from exc
        except OSError as exc:
            msg = f"OS error during copy from '{source_path}' to '{dest_path}'"
            self.logger.error(msg)
            raise IOError(msg) from exc

    def copy_directory(
        self, source_dir: Path, dest_dir: Path, exist_ok: bool = False
    ) -> None:
        """Recursively copy a directory tree."""
        self.logger.debug(
            "Attempting to copy directory from '%s' to '%s'", source_dir, dest_dir
        )
        if not source_dir.is_dir():
            msg = f"Source directory does not exist or is not a directory: {source_dir}"
            self.logger.error(msg)
            raise NotADirectoryError(msg)
        if dest_dir.exists() and dest_dir.is_file():
            msg = f"Destination path exists as a file: {dest_dir}"
            self.logger.error(msg)
            raise FileExistsError(msg)
        try:
            dest_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_dir, dest_dir, dirs_exist_ok=exist_ok)
            self.logger.debug(
                "Successfully copied directory '%s' to '%s'", source_dir, dest_dir
            )
        except (FileNotFoundError, NotADirectoryError) as exc:
            msg = f"Source directory does not exist or is not a directory: {source_dir}"
            self.logger.error(msg)
            raise NotADirectoryError(msg) from exc
        except FileExistsError as exc:
            msg = f"Destination path exists: {dest_dir}"
            self.logger.error(msg)
            raise FileExistsError(msg) from exc
        except shutil.Error as exc:
            msg = f"An error occurred during '{source_dir}' copy"
            self.logger.error(msg)
            raise IOError(msg) from exc
        except OSError as exc:
            msg = f"A system error occurred during '{source_dir}' copy"
            self.logger.error(msg)
            raise IOError(msg) from exc

    def create_directory(self, dir_path: Path, exist_ok: bool = True) -> None:
        """Create a directory (and parents)."""
        self.logger.debug("Ensuring directory exists: %s", dir_path)
        try:
            dir_path.mkdir(parents=True, exist_ok=exist_ok)
            self.logger.debug("Directory ensured: %s", dir_path)
        except PermissionError as exc:
            msg = f"Permission denied when creating directory: {dir_path}"
            self.logger.error(msg)
            raise PermissionError(msg) from exc
        except OSError as exc:
            msg = f"OS error occurred while creating directory: {dir_path}"
            self.logger.error(msg)
            raise IOError(msg) from exc

    def list_files(
        self,
        directory: Path,
        recursive: bool = False,
        extensions: Optional[List[str]] = None,
    ) -> List[Path]:
        """List files in a directory, optionally recursively and filtered by extension."""
        self.logger.debug("Listing files in '%s' (recursive=%s)", directory, recursive)
        if not directory.exists():
            msg = f"Directory not found for listing: {directory}"
            self.logger.error(msg)
            raise FileNotFoundError(msg)
        if not directory.is_dir():
            msg = f"Path is not a directory: {directory}"
            self.logger.error(msg)
            raise NotADirectoryError(msg)

        normalized_exts = self._normalize_extensions(extensions)
        found_files: List[Path] = []
        try:
            paths = directory.rglob("*") if recursive else directory.iterdir()
            for path in paths:
                if path.is_file() and (
                    normalized_exts is None or path.suffix.lower() in normalized_exts
                ):
                    found_files.append(path.resolve())
            found_files.sort()
            self.logger.info("Found %d files in '%s'", len(found_files), directory)
            return found_files
        except OSError as exc:
            msg = f"OS error occurred while listing files in: {directory}"
            self.logger.error(msg)
            raise IOError(msg) from exc

    def path_exists(self, path: Path) -> bool:
        """Return whether a path exists."""
        return path.exists()

    def _normalize_extensions(
        self, extensions: Optional[List[str]]
    ) -> Optional[List[str]]:
        """Lower-case extensions and ensure each has a leading dot."""
        if not extensions:
            return None
        return [
            ext.lower() if ext.startswith(".") else f".{ext.lower()}"
            for ext in extensions
        ]
