from typing import List, Optional
import os
import shutil
import logging


class FileSystemManager:
    """
    Manages file system operations such as reading, writing, copying files,
    creating directories, listing files, and checking path existence.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def read_file(self, filepath: str) -> str:
        """
        Reads the content of a file.

        Args:
            filepath: The path to the file.

        Returns:
            The content of the file as a string.

        Raises:
            FileNotFoundError: If the file does not exist.
            PermissionError: If permission is denied when reading.
            IOError: For other OS-level errors.
        """
        self.logger.debug(f"Attempting to read file: {filepath}")
        try:
            with open(filepath, "r", encoding="utf-8") as file:
                content = file.read()
                self.logger.info(f"Successfully read file: {filepath}")
                return content
        except FileNotFoundError as e:
            msg = f"File not found at path: {filepath}"
            self.logger.error(msg)
            raise FileNotFoundError(msg) from e
        except PermissionError as e:
            msg = f"Permission denied when reading file: {filepath}"
            self.logger.error(msg)
            raise PermissionError(msg) from e
        except OSError as e:
            msg = f"OS error occurred while reading file: {filepath}"
            self.logger.error(msg)
            raise IOError(msg) from e

    def write_file(self, filepath: str, content: str) -> None:
        """
        Writes content to a file, creating the directory if it does not exist.

        Args:
            filepath: Path to the file.
            content: Content to write.

        Raises:
            PermissionError: If writing is denied.
            IOError: For other OS-related errors.
        """
        self.logger.debug(f"Attempting to write file to: {filepath}")
        try:
            directory = os.path.dirname(filepath)
            if directory:
                self.create_directory(directory)
            with open(filepath, "w", encoding="utf-8") as file:
                file.write(content)
            self.logger.info(f"Successfully wrote file: {filepath}")
        except PermissionError as e:
            msg = f"Permission denied when writing to file: {filepath}"
            self.logger.error(msg)
            raise PermissionError(msg) from e
        except OSError as e:
            msg = f"OS error occurred while writing file: {filepath}"
            self.logger.error(msg)
            raise IOError(msg) from e

    def copy_file(self, source_path: str, dest_path: str) -> None:
        """
        Copies a file from source_path to dest_path, ensuring destination directory exists.

        Args:
            source_path: Path to the source file.
            dest_path: Path to the destination file.

        Raises:
            FileNotFoundError: If source file does not exist.
            PermissionError: If access is denied.
            IOError: For other OS-related errors.
        """
        self.logger.debug(f"Attempting to copy from '{source_path}' to '{dest_path}'")
        try:
            dest_dir = os.path.dirname(dest_path)
            if dest_dir:
                self.create_directory(dest_dir)
            shutil.copy2(source_path, dest_path)
            self.logger.info(f"Successfully copied '{source_path}' to '{dest_path}'")
        except FileNotFoundError as e:
            msg = f"Source file for copy not found: {source_path}"
            self.logger.error(msg)
            raise FileNotFoundError(msg) from e
        except shutil.SameFileError:
            self.logger.warning(
                f"Source and destination are the same file: {source_path}"
            )
        except PermissionError as e:
            msg = f"Permission denied during copy from '{source_path}' to '{dest_path}'"
            self.logger.error(msg)
            raise PermissionError(msg) from e
        except OSError as e:
            msg = f"OS error during copy from '{source_path}' to '{dest_path}'"
            self.logger.error(msg)
            raise IOError(msg) from e

    def copy_directory(
        self, source_dir: str, dest_dir: str, exist_ok: bool = False
    ) -> None:
        """
        Recursively copies a directory from a source to a destination.

        Args:
            source_dir: The path to the source directory.
            dest_dir: The path to the destination directory.
            exist_ok: If False (default), raises an error if dest_dir exists.
                    If True, existing files in the destination may be overwritten.

        Raises:
            NotADirectoryError: If the source is not a directory.
            FileExistsError: If the destination exists and is a file.
            IOError: For other OS-level copying errors.
        """
        self.logger.debug(
            f"Attempting to copy directory from '{source_dir}' to '{dest_dir}'"
        )

        if self.path_exists(dest_dir) and not os.path.isdir(dest_dir):
            msg = f"Destination path exists and is not a directory: {dest_dir}"
            self.logger.error(msg)
            raise FileExistsError(msg)

        try:
            # shutil.copytree handles the recursive copy.
            # The `dirs_exist_ok` parameter was added in Python 3.8 and aligns with our `exist_ok`.
            shutil.copytree(source_dir, dest_dir, dirs_exist_ok=exist_ok)
            self.logger.info(
                f"Successfully copied directory '{source_dir}' to '{dest_dir}'"
            )
        except NotADirectoryError as e:
            msg = (
                f"Source directory for copy does not exist or it is file: {source_dir}"
            )
            self.logger.error(msg)
            raise NotADirectoryError(msg) from e
        except FileExistsError as e:
            msg = f"Destination path exists and is not a directory: {dest_dir}"
            self.logger.error(msg)
            raise FileExistsError(msg) from e
        except shutil.Error as e:
            msg = f"An error occurred during '{source_dir}' copy"
            self.logger.error(msg)
            raise IOError(msg) from e
        except OSError as e:
            # OSError reports lower-level problems (e.g., permissions, disk full)
            msg = f"A system error occurred during '{source_dir}' copy"
            self.logger.error(msg)
            raise IOError(msg) from e

    def create_directory(self, dir_path: str, exist_ok: bool = True) -> None:
        """
        Creates a directory and any necessary parents.

        Args:
            dir_path: Directory path to create.
            exist_ok: If True, no error if directory exists.

        Raises:
            PermissionError: If creation denied.
            IOError: For other OS errors.
        """
        self.logger.debug(f"Ensuring directory exists: {dir_path}")
        try:
            os.makedirs(dir_path, exist_ok=exist_ok)
        except PermissionError as e:
            msg = f"Permission denied when creating directory: {dir_path}"
            self.logger.error(msg)
            raise PermissionError(msg) from e
        except OSError as e:
            msg = f"OS error occurred while creating directory: {dir_path}"
            self.logger.error(msg)
            raise IOError(msg) from e

    def list_files(
        self,
        directory: str,
        recursive: bool = False,
        extensions: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Lists files in a directory, optionally recursively and filtered by extensions.

        Args:
            directory: Directory to scan.
            recursive: If True, include subdirectories.
            extensions: List of file extensions to filter by (case-insensitive).

        Returns:
            List of absolute file paths.

        Raises:
            FileNotFoundError: If directory does not exist.
            NotADirectoryError: If path is not a directory.
            IOError: For other OS errors.
        """
        self.logger.debug(f"Listing files in '{directory}' (recursive={recursive})")
        found_files = []
        normalized_exts = (
            [
                ext.lower() if ext.startswith(".") else f".{ext.lower()}"
                for ext in extensions
            ]
            if extensions
            else None
        )

        try:
            if recursive:
                for root, _, files in os.walk(directory):
                    for file in files:
                        ext = os.path.splitext(file)[1].lower()
                        if normalized_exts is None or ext in normalized_exts:
                            found_files.append(
                                os.path.abspath(os.path.join(root, file))
                            )
            else:
                for entry in os.listdir(directory):
                    entry_path = os.path.join(directory, entry)
                    if os.path.isfile(entry_path):
                        ext = os.path.splitext(entry)[1].lower()
                        if normalized_exts is None or ext in normalized_exts:
                            found_files.append(os.path.abspath(entry_path))
            self.logger.info(f"Found {len(found_files)} files in '{directory}'")
            return found_files
        except FileNotFoundError as e:
            msg = f"Directory not found for listing: {directory}"
            self.logger.error(msg)
            raise FileNotFoundError(msg) from e
        except NotADirectoryError as e:
            msg = f"Path is not a directory: {directory}"
            self.logger.error(msg)
            raise NotADirectoryError(msg) from e
        except OSError as e:
            msg = f"OS error occurred while listing files in: {directory}"
            self.logger.error(msg)
            raise IOError(msg) from e

    def path_exists(self, filepath: str) -> bool:
        """
        Checks if a path exists.

        Args:
            filepath: Path to check.

        Returns:
            True if path exists, else False.
        """
        return os.path.exists(filepath)
