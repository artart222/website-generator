import json
import os
import sys
from pathlib import Path

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from core.config import Config  # noqa: E402
from core.project import Project  # noqa: E402
from core.page import Page  # noqa: E402


def test_inject_css_order_respects_config():
    config = Config()
    config.settings["plugins"] = ["TestPluginB", "TestPluginA"]
    config.settings["navigation"] = []

    project = Project(config)
    page = Page(Path("dummy.md"), config, project.fs_manager)
    page.set_processed_content("")
    page.add_metadata({"title": ["Dummy"]})
    page.set_title()
    page.set_slug()
    page.calculate_output_path(Path(config.get("output_directory")))

    context = project._build_page_context(page, header="")
    stylesheets = context["stylesheets"]

    assert stylesheets[-2:] == ["/b.css", "/a.css"]


def test_modify_template_context_merges_in_order():
    config = Config()
    config.settings["plugins"] = ["TestPluginA", "TestPluginB"]
    config.settings["navigation"] = []

    project = Project(config)
    page = Page(Path("dummy.md"), config, project.fs_manager)
    page.set_processed_content("")
    page.add_metadata({"title": ["Dummy"]})
    page.set_title()
    page.set_slug()
    page.calculate_output_path(Path(config.get("output_directory")))

    context = project._build_page_context(page, header="")

    assert context["order"] == "b"


def test_export_json_per_page(tmp_path):
    output_dir = tmp_path / "output"
    data_dir = output_dir / "data"

    config = Config()
    config.settings["output_directory"] = str(output_dir)
    config.settings["navigation"] = []
    config.settings["frontend"]["export_data"]["enabled"] = True
    config.settings["frontend"]["export_data"]["output_dir"] = str(data_dir)

    project = Project(config)
    page = Page(Path("dummy.md"), config, project.fs_manager)
    page.set_processed_content("<p>Hello</p>")
    page.add_metadata({"title": ["Hello"], "type": "blog"})
    page.set_title()
    page.set_slug()
    page.set_page_type("blog")
    page.calculate_output_path(Path(config.get("output_directory")))
    page.generate_abs_url()
    page.generate_root_rel_url()
    project.site.add_page(page)

    project._export_json_data()

    rel_output_path = page.get_output_path().relative_to(output_dir)
    page_json_path = data_dir / rel_output_path.with_suffix(".json")
    site_json_path = data_dir / "site.json"

    assert page_json_path.exists()
    assert site_json_path.exists()

    site_payload = json.loads(site_json_path.read_text(encoding="utf-8"))
    assert site_payload["pages"]
    assert site_payload["pages"][0]["json_path"].endswith(
        str(page_json_path.relative_to(output_dir)).replace(os.sep, "/")
    )
