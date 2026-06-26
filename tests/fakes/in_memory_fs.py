"""In-memory filesystem fake for unit tests."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class InMemoryFileSystem:
    """Minimal :class:`~wg_contracts.ports.FileSystemPort` for isolated builds."""

    def __init__(self, files: dict[str, str] | None = None) -> None:
        self._files: dict[str, str] = dict(files or {})
        self._dirs: set[str] = set()

    def _key(self, filepath: Path) -> str:
        return filepath.as_posix()

    def read_file(self, filepath: Path) -> str:
        key = self._key(filepath)
        if key not in self._files:
            raise FileNotFoundError(key)
        return self._files[key]

    def write_file(self, filepath: Path, content: str) -> None:
        key = self._key(filepath)
        parent = str(Path(key).parent)
        if parent and parent != ".":
            self._dirs.add(parent)
        self._files[key] = content

    def copy_file(self, source_path: Path, dest_path: Path) -> None:
        self.write_file(dest_path, self.read_file(source_path))

    def copy_directory(
        self, source_dir: Path, dest_dir: Path, exist_ok: bool = False
    ) -> None:
        prefix = source_dir.as_posix().rstrip("/") + "/"
        dest_prefix = dest_dir.as_posix().rstrip("/") + "/"
        for key, content in list(self._files.items()):
            if key.startswith(prefix):
                relative = key[len(prefix) :]
                self.write_file(Path(dest_prefix + relative), content)

    def create_directory(self, dir_path: Path, exist_ok: bool = True) -> None:
        self._dirs.add(self._key(dir_path))

    def list_files(
        self,
        directory: Path,
        recursive: bool = False,
        extensions: Optional[list[str]] = None,
    ) -> list[Path]:
        prefix = directory.as_posix().rstrip("/") + "/"
        results: list[Path] = []
        for key in self._files:
            if not key.startswith(prefix):
                continue
            relative = key[len(prefix) :]
            if not recursive and "/" in relative:
                continue
            path = Path(key)
            if extensions and path.suffix.lstrip(".") not in extensions:
                continue
            results.append(path)
        return sorted(results)

    def path_exists(self, path: Path) -> bool:
        key = self._key(path)
        return key in self._files or key in self._dirs
