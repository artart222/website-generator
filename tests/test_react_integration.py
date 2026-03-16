import os
import sys

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from core.config import Config  # noqa: E402
from core.project import Project  # noqa: E402


def test_react_build_skips_when_disabled():
    config = Config()
    config.settings["react"]["enabled"] = False

    project = Project(config)
    project._build_react_section()
