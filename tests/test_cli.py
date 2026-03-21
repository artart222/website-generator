import os
import sys
from pathlib import Path
import tempfile

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from cli import build_parser, cmd_theme_create  # noqa: E402


def test_cli_parser_supports_theme_eject():
    parser = build_parser()
    args = parser.parse_args(["theme", "eject", "partials/header.html"])
    assert args.target == "partials/header.html"


def test_theme_create_scaffolds_manifest(monkeypatch):
    with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        temp_path = Path(temp_dir)
        monkeypatch.chdir(temp_path)
        cmd_theme_create(type("Args", (), {"name": "demo-theme"})())

        assert (temp_path / "themes" / "demo-theme" / "theme.yaml").exists()
        assert (temp_path / "themes" / "demo-theme" / "layouts" / "base.html").exists()
