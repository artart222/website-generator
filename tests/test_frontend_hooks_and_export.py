import json
import os
import sys
from pathlib import Path
import tempfile

import pytest

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from core.config import Config  # noqa: E402
from core.page import Page  # noqa: E402
from core.plugin_manager import PluginManager  # noqa: E402
from core.project import Project  # noqa: E402
from tests.support_plugins import TestPluginA, TestPluginB  # noqa: E402


@pytest.fixture(autouse=True)
def use_test_plugins(monkeypatch):
    discovered_plugins = {
        "TestPluginA": TestPluginA,
        "TestPluginB": TestPluginB,
    }

    def detect_and_load_test_plugins(self):
        self.plugins = [
            discovered_plugins[name]()
            for name in self.config.get("plugins", [])
            if name in discovered_plugins
        ]
        return self.plugins

    monkeypatch.setattr(
        PluginManager,
        "detect_and_load_plugins",
        detect_and_load_test_plugins,
    )


def test_inject_css_order_respects_config():
    config = Config()
    config.settings["plugins"] = ["TestPluginB", "TestPluginA"]
    config.settings["site"]["navigation"] = []

    project = Project(config)
    page = Page(Path("dummy.md"), config, project.fs_manager)
    page.set_processed_content("")
    page.add_metadata({"title": "Dummy"})
    page.calculate_output_path(Path(config.get("build.output_directory")))
    page.generate_root_rel_url()
    page.generate_abs_url()

    context = project._build_page_context(page, header="", navigation_items=[])
    stylesheets = context["stylesheets"]

    assert stylesheets[-2:] == ["/b.css", "/a.css"]


def test_modify_template_context_merges_in_order():
    config = Config()
    config.settings["plugins"] = ["TestPluginA", "TestPluginB"]
    config.settings["site"]["navigation"] = []

    project = Project(config)
    page = Page(Path("dummy.md"), config, project.fs_manager)
    page.set_processed_content("")
    page.add_metadata({"title": "Dummy"})
    page.calculate_output_path(Path(config.get("build.output_directory")))
    page.generate_root_rel_url()
    page.generate_abs_url()

    context = project._build_page_context(page, header="", navigation_items=[])

    assert context["order"] == "b"


def test_export_json_per_page():
    with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        temp_path = Path(temp_dir)
        output_dir = temp_path / "output"
        data_dir = output_dir / "data"

        config = Config()
        config.settings["build"]["output_directory"] = str(output_dir)
        config.settings["site"]["navigation"] = []
        config.settings["experimental"]["export_data"]["enabled"] = True
        config.settings["experimental"]["export_data"]["output_dir"] = str(data_dir)

        project = Project(config)
        page = Page(Path("dummy.md"), config, project.fs_manager)
        page.set_processed_content("<p>Hello</p>")
        page.add_metadata({"title": "Hello", "type": "blog", "layout": "document"})
        page.set_page_type("blog")
        page.collection = "blog"
        page.calculate_output_path(Path(config.get("build.output_directory")), url_prefix="blog")
        page.generate_root_rel_url()
        page.generate_abs_url()
        project.site.add_page(page)

        project._export_json_data()

        page_json_path = data_dir / "blog" / "hello" / "page.json"
        site_json_path = data_dir / "site.json"

        assert page_json_path.exists()
        assert site_json_path.exists()

        site_payload = json.loads(site_json_path.read_text(encoding="utf-8"))
        assert site_payload["pages"][0]["collection"] == "blog"


def test_export_json_filters_collections():
    with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        temp_path = Path(temp_dir)
        output_dir = temp_path / "output"
        data_dir = output_dir / "data"

        config = Config()
        config.settings["build"]["output_directory"] = str(output_dir)
        config.settings["site"]["navigation"] = []
        config.settings["experimental"]["export_data"]["enabled"] = True
        config.settings["experimental"]["export_data"]["output_dir"] = str(data_dir)
        config.settings["experimental"]["export_data"]["include_collections"] = ["docs"]

        project = Project(config)
        for collection_name in ["blog", "docs"]:
            page = Page(Path(f"{collection_name}.md"), config, project.fs_manager)
            page.set_processed_content(f"<p>{collection_name}</p>")
            page.add_metadata(
                {"title": collection_name.title(), "type": collection_name, "layout": "document"}
            )
            page.set_page_type(collection_name)
            page.collection = collection_name
            page.calculate_output_path(
                Path(config.get("build.output_directory")), url_prefix=collection_name
            )
            page.generate_root_rel_url()
            page.generate_abs_url()
            project.site.add_page(page)

        project._export_json_data()

        site_payload = json.loads((data_dir / "site.json").read_text(encoding="utf-8"))
        collections = [entry["collection"] for entry in site_payload["pages"]]
        assert collections == ["docs"]
