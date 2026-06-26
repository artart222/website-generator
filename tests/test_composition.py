"""Composition-root tests with injected fakes."""

from __future__ import annotations

from pathlib import Path

from core.composition import build_project
from core.config import Config
from tests.fakes.in_memory_fs import InMemoryFileSystem


def test_build_project_accepts_in_memory_filesystem():
    config = Config()
    config.settings["build"]["output_directory"] = "./output"
    config.settings["content"]["collections"] = {}
    config.settings["plugins"] = []

    fs = InMemoryFileSystem()
    fs.write_file(Path("theme.settings.yaml"), "preset: default\n")
    theme_manifest = Path("themes/minimal-blog/theme.yaml")
    if theme_manifest.exists():
        fs.write_file(theme_manifest, theme_manifest.read_text(encoding="utf-8"))

    project = build_project(config, fs_manager=fs)
    assert project.fs_manager is fs

    fs.write_file(Path("probe.txt"), "wired")
    assert fs.read_file(Path("probe.txt")) == "wired"
