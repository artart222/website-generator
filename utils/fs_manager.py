import os
import shutil


class FileSystemManager:
    """
    Manages file system operations like reading, writing, and copying files,
    creating directories, and checking path existence.

    Methods:
    read_file(filepath: str) -> str
    write_file(filepath: str, content: str)
    copy_file(source_path: str, dest_path: str)
    create_directory(dir_path: str, exist_ok: bool = True)
    list_files(directory: str, recursive: bool = False, extensions: list[str] | None = None) -> list[str]
    path_exists(filepath: str) -> bool
    """

    def __init__(self) -> None:
        pass

    def read_file(self, filepath: str) -> str:
        """
        Reads the content of a file.

        Args:
            filepath: The path to the file.

        Returns:
            The content of the file as a string.

        Raises:
            FileNotFoundError: If the file does not exist.
            Exception: For other unexpected errors.
        """

        if not self.path_exists(filepath):
            raise FileNotFoundError(f"No such file: {filepath}")
        try:
            with open(filepath, "r", encoding="utf-8") as file:
                return file.read()
        except Exception as e:
            raise Exception(
                f"An unexpected error occurred while reading {filepath}"
            ) from e

    def write_file(self, filepath: str, content: str):
        """
        Writes given content to a file.

        Args:
            filepath: The path to the file.
            content: The content of the file as a string.

        Raises:
            IOError: If directory creation or file writing fails.
            Exception: For any unexpected errors.
        """
        dest_dir = os.path.dirname(filepath)
        if dest_dir:
            try:
                self.create_directory(dest_dir, exist_ok=True)
            except Exception as e:
                raise IOError(
                    f"Failed to ensure destination directory '{dest_dir}' for writing to '{filepath}'. Error: {e}"
                ) from e
        try:
            with open(filepath, "w", encoding="utf-8") as output_file:
                output_file.write(content)
        except IOError as e:
            raise IOError(
                f"IOError occurred while writing to file {filepath}: {e}"
            ) from e
        except Exception as e:
            raise Exception(
                f"An unexpected error occurred while writing {filepath}: {e}"
            ) from e

    def copy_file(self, source_path: str, dest_path: str):
        """
        Copies a file from source_path to dest_path.
        Ensures the destination directory exists.
        Uses shutil.copy2 to preserve metadata.

        Args:
            source_path: The path to the source file.
            dest_path: The path to the destination file.

        Raises:
            FileNotFoundError: If the source_path does not exist or is not a file.
            Exception: For other unexpected errors.
        """
        if not self.path_exists(source_path):
            raise FileNotFoundError(f"No such source: {source_path}")

        # Ensure destination directory exists
        dest_dir = os.path.dirname(dest_path)
        if dest_dir:
            try:
                self.create_directory(dest_dir)
            except Exception as e:
                raise IOError(
                    f"Failed to create destination directory '{dest_dir}' for copy operation. Error: {e}"
                ) from e
        try:
            shutil.copytree(source_path, dest_path)
        except Exception as e:
            raise Exception(
                f"An unexpected error occurred while copying {source_path}: {e}"
            )

    def create_directory(self, dir_path: str, exist_ok: bool = True):
        """
        Creates a directory, including any necessary parent directories.

        Args:
            dir_path: The absolute path of the directory to create.
            exist_ok: If True (default), no error is raised if the
                      target directory already exists. If False,
                      FileExistsError is raised if the target directory exists.

        Raises:
            IOError: If an OS-level error occurs during directory creation
                     (and it's not a FileExistsError when exist_ok=False).
            Exception: For other unexpected errors.
        """

        try:
            os.makedirs(dir_path, exist_ok=exist_ok)
        except FileExistsError as e:
            # This error is only relevant if exist_ok=False.
            # If exist_ok=True, os.makedirs handles it silently.
            # However, os.makedirs should not raise FileExistsError if exist_ok=True.
            # This block is more of a safeguard or for scenarios where exist_ok might be False.
            raise FileExistsError(
                f"Directory already exists and exist_ok=False: '{dir_path}'. Original error: {e}"
            ) from e  # Re-raise the specific FileExistsError
        except OSError as e:  # Catches other OS-level errors like permission denied
            raise IOError(
                f"OSError occurred while creating directory '{dir_path}': {e}"
            ) from e  # Wrap OSError in IOError for consistency if desired, or re-raise OSError
        except Exception as e:  # Catch any other unexpected errors
            raise Exception(
                f"An unexpected error occurred while creating directory '{dir_path}': {e}"
            ) from e

    def list_files(
        self,
        directory: str,
        recursive: bool = False,
        extensions: list[str] | None = None,
    ) -> list[str]:
        """
        Lists files in a given directory, optionally recursively and filtered by extensions.

        Args:
            directory: The absolute path to the directory to scan.
            recursive: If True, scan subdirectories recursively. Defaults to False.
            extensions: A list of file extensions to include (e.g., ['.txt', '.md']).
                        Matching is case-insensitive. If None, all files are included.
                        Defaults to None.

        Returns:
            A list of absolute paths to the found files.

        Raises:
            FileNotFoundError: If the directory does not exist.
            NotADirectoryError: If the path exists but is not a directory.
            IOError: For other OS-level errors during listing.
        """
        if not self.path_exists(directory):
            raise FileNotFoundError(f"Directory not found for listing: {directory}")

        if not os.path.isdir(directory):
            raise NotADirectoryError(
                f"Path is not a directory, cannot list files: {directory}"
            )

        found_files = []

        # Normalize extensions to lowercase and ensure they start with a dot for consistent matching
        normalized_extensions = None
        if extensions:
            normalized_extensions = [
                ext.lower() if ext.startswith(".") else f".{ext.lower()}"
                for ext in extensions
            ]
        try:
            if recursive:
                for root, _dirs, files in os.walk(directory):
                    for filename in files:
                        if normalized_extensions:
                            file_ext = os.path.splitext(filename)[1].lower()
                            if file_ext in normalized_extensions:
                                found_files.append(
                                    os.path.abspath(os.path.join(root, filename))
                                )
                        else:
                            found_files.append(
                                os.path.abspath(os.path.join(root, filename))
                            )
            else:  # Not recursive
                for item_name in os.listdir(directory):
                    item_path = os.path.abspath(os.path.join(directory, item_name))
                    if os.path.isfile(item_path):
                        if normalized_extensions:
                            file_ext = os.path.splitext(item_name)[1].lower()
                            if file_ext in normalized_extensions:
                                found_files.append(item_path)
                        else:
                            found_files.append(item_path)
        except OSError as e:
            raise IOError(
                f"OSError occurred while listing files in '{directory}': {e}"
            ) from e
        except Exception as e:
            raise Exception(
                f"An unexpected error occurred while listing files in '{directory}': {e}"
            ) from e
        return found_files

    def path_exists(self, filepath: str) -> bool:
        """
        Checks if a given path exists on the file system.

        This method is a wrapper around os.path.exists().

        Args:
            filepath: The path to a file or directory.

        Returns:
            True if the path exists, False otherwise.
        """
        return os.path.exists(filepath)
