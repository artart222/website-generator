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


def _write_markdown(path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"Title: {title}\n\n# {title}\n", encoding="utf-8")


def test_discover_pages_by_collection_and_type(tmp_path):
    blogs_dir = tmp_path / "blogs"
    pages_dir = tmp_path / "pages"

    _write_markdown(blogs_dir / "post.md", "Blog Post")
    _write_markdown(pages_dir / "about.md", "About Page")

    config = Config()
    config.settings["output_directory"] = str(tmp_path / "output")
    config.settings["collections"] = {
        "blog": {"path": str(blogs_dir), "type": "blog", "url_prefix": "blog"},
        "pages": {"path": str(pages_dir), "type": "page"},
    }
    config.settings["navigation"] = []

    project = Project(config)
    project._discover_and_load_pages()

    assert len(project.site.pages) == 2

    blog_page = next(p for p in project.site.pages if p.collection == "blog")
    page_page = next(p for p in project.site.pages if p.collection == "pages")

    assert blog_page.page_type == "blog"
    assert page_page.page_type == "page"
    assert "blog" in str(blog_page.get_output_path())


def test_template_resolution_precedence():
    config = Config()
    config.settings["templates_by_type"] = {"blog": "type.html"}
    project = Project(config)

    page = Page(Path("dummy.md"), config, project.fs_manager)
    page.page_type = "blog"
    page.collection_config = {"template": "collection.html"}

    page.metadata = {"template": "meta.html"}
    assert project._resolve_template_name(page) == "meta.html"

    page.metadata = {}
    assert project._resolve_template_name(page) == "collection.html"

    page.collection_config = None
    assert project._resolve_template_name(page) == "type.html"


def test_url_prefix_output_path(tmp_path):
    config = Config()
    project = Project(config)
    page = Page(Path("dummy.md"), config, project.fs_manager)
    page.slug = "test"

    output_dir = tmp_path / "output"
    page.calculate_output_path(output_dir, url_prefix="docs")
    assert str(page.get_output_path()).endswith(
        str(Path("docs") / "test" / "index.html")
    )

    page.calculate_output_path(output_dir, url_prefix="")
    assert str(page.get_output_path()).endswith(str(Path("test") / "index.html"))


def test_load_site_data(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "products.json").write_text(
        '{"items": ["a", "b"]}', encoding="utf-8"
    )
    (data_dir / "settings.yaml").write_text("theme: light\n", encoding="utf-8")

    config = Config()
    config.settings["data_dir"] = str(data_dir)
    project = Project(config)
    project._load_site_data()

    assert project.site.data["products"]["items"] == ["a", "b"]
    assert project.site.data["settings"]["theme"] == "light"
