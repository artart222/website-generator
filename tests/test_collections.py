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
from core.project import Project  # noqa: E402


def _write_markdown(path: Path, title: str, page_type: str = "page") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
title: {title}
type: {page_type}
---

# {title}
""",
        encoding="utf-8",
    )


def _supports_python_dir_creation() -> bool:
    try:
        with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir:
            (Path(temp_dir) / "probe").mkdir(parents=True, exist_ok=True)
        return True
    except PermissionError:
        return False


def test_discover_pages_by_collection_and_type():
    if not _supports_python_dir_creation():
        pytest.skip("Current interpreter cannot create directories in this environment.")

    with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        temp_path = Path(temp_dir)
        blogs_dir = temp_path / "blogs"
        pages_dir = temp_path / "pages"

        _write_markdown(blogs_dir / "post.md", "Blog Post", "blog")
        _write_markdown(pages_dir / "about.md", "About Page", "page")

        config = Config()
        config.settings["build"]["output_directory"] = str(temp_path / "output")
        config.settings["content"]["collections"] = {
            "blog": {
                "path": str(blogs_dir),
                "type": "blog",
                "route": {"prefix": "blog"},
                "layout": "document",
                "index": {"enabled": True, "layout": "collection"},
            },
            "pages": {
                "path": str(pages_dir),
                "type": "page",
                "route": {"prefix": ""},
                "layout": "document",
            },
        }
        config.settings["site"]["navigation"] = []

        project = Project(config)
        project._discover_and_load_pages()

        assert len(project.site.pages) == 2

        blog_page = next(p for p in project.site.pages if p.collection == "blog")
        page_page = next(p for p in project.site.pages if p.collection == "pages")

        assert blog_page.page_type == "blog"
        assert page_page.page_type == "page"
        assert blog_page.get_route_prefix() == "blog"


def test_template_resolution_prefers_layout_then_collection_then_type_map():
    config = Config()
    config.settings["content"]["templates_by_type"] = {"blog": "document"}
    project = Project(config)

    page = Page(Path("dummy.md"), config, project.fs_manager)
    page.page_type = "blog"
    page.collection_config = {"layout": "collection"}

    page.metadata = {"layout": "document"}
    page._populate_attributes()
    assert project._resolve_template_name(page) == "layouts/document.html"

    page.metadata = {}
    page.layout = None
    assert project._resolve_template_name(page) == "layouts/collection.html"

    page.collection_config = None
    assert project._resolve_template_name(page) == "layouts/document.html"


def test_assign_routes_uses_collection_prefix_and_root_index():
    if not _supports_python_dir_creation():
        pytest.skip("Current interpreter cannot create directories in this environment.")

    with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        temp_path = Path(temp_dir)
        blogs_dir = temp_path / "blogs"
        pages_dir = temp_path / "pages"
        _write_markdown(blogs_dir / "post.md", "Blog Post", "blog")
        _write_markdown(pages_dir / "home.md", "Home", "index")

        config = Config()
        config.settings["build"]["output_directory"] = str(temp_path / "output")
        config.settings["content"]["collections"] = {
            "blog": {
                "path": str(blogs_dir),
                "type": "blog",
                "route": {"prefix": "blog"},
                "layout": "document",
            },
            "pages": {
                "path": str(pages_dir),
                "type": "page",
                "route": {"prefix": ""},
                "layout": "document",
            },
        }
        project = Project(config)
        project._discover_and_load_pages()
        project._assign_routes()

        home_page = next(p for p in project.site.pages if p.page_type == "index")
        blog_page = next(p for p in project.site.pages if p.collection == "blog")

        assert home_page.get_root_rel_url() == "/"
        assert blog_page.get_root_rel_url() == "/blog/blog-post/"


def test_collection_index_plugin_generates_collection_page():
    if not _supports_python_dir_creation():
        pytest.skip("Current interpreter cannot create directories in this environment.")

    with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        temp_path = Path(temp_dir)
        blogs_dir = temp_path / "blogs"
        _write_markdown(blogs_dir / "post.md", "Blog Post", "blog")

        config = Config()
        config.settings["plugins"] = ["CollectionIndexerPlugin"]
        config.settings["build"]["output_directory"] = str(temp_path / "output")
        config.settings["content"]["collections"] = {
            "blog": {
                "path": str(blogs_dir),
                "type": "blog",
                "route": {"prefix": "blog"},
                "layout": "document",
                "index": {
                    "enabled": True,
                    "layout": "collection",
                    "title": "Blog",
                    "output_path": "blog/index.html",
                },
            }
        }

        project = Project(config)
        project._discover_and_load_pages()
        project._assign_routes()
        project.plugin_manager.run_hook(
            "after_collections_loaded",
            site=project.site,
            config=project.config,
            fs_manager=project.fs_manager,
        )
        project._assign_routes()

        index_page = project.site.get_collection_index_page("blog")
        assert index_page is not None
        assert index_page.get_root_rel_url() == "/blog/"
        assert "/blog/blog-post/" in index_page.processed_content


def test_collection_index_plugin_renders_product_meta():
    if not _supports_python_dir_creation():
        pytest.skip("Current interpreter cannot create directories in this environment.")

    with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        temp_path = Path(temp_dir)
        shop_dir = temp_path / "shop"
        shop_dir.mkdir(parents=True, exist_ok=True)
        (shop_dir / "tea-set.md").write_text(
            """---
title: Tea Set
type: product
sku: TEA-SET-01
price: 1890000
currency: IRR
availability: in_stock
summary: Static product page.
---

# Tea Set
""",
            encoding="utf-8",
        )

        config = Config()
        config.settings["plugins"] = ["CollectionIndexerPlugin"]
        config.settings["build"]["output_directory"] = str(temp_path / "output")
        config.settings["content"]["collections"] = {
            "shop": {
                "path": str(shop_dir),
                "type": "product",
                "model": "product",
                "route": {"prefix": "shop"},
                "layout": "document",
                "index": {
                    "enabled": True,
                    "layout": "collection",
                    "title": "Shop",
                    "output_path": "shop/index.html",
                },
            }
        }

        project = Project(config)
        project._discover_and_load_pages()
        project._apply_content_models()
        project._assign_routes()
        project.plugin_manager.run_hook(
            "after_collections_loaded",
            site=project.site,
            config=project.config,
            fs_manager=project.fs_manager,
        )

        index_page = project.site.get_collection_index_page("shop")
        assert index_page is not None
        assert "IRR 1,890,000" in index_page.processed_content
        assert "in stock" in index_page.processed_content
        assert "Buy now" in index_page.processed_content


def test_build_cleans_stale_output_files():
    if not _supports_python_dir_creation():
        pytest.skip("Current interpreter cannot create directories in this environment.")

    with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir:
        temp_path = Path(temp_dir)
        pages_dir = temp_path / "pages"
        output_dir = temp_path / "output"
        _write_markdown(pages_dir / "home.md", "Home", "index")
        output_dir.mkdir(parents=True, exist_ok=True)
        stale_file = output_dir / "stale.txt"
        stale_file.write_text("stale", encoding="utf-8")

        config = Config()
        config.settings["build"]["output_directory"] = str(output_dir)
        config.settings["content"]["collections"] = {
            "pages": {
                "path": str(pages_dir),
                "type": "page",
                "route": {"prefix": ""},
                "layout": "document",
            }
        }
        config.settings["site"]["navigation"] = []

        project = Project(config)
        project.build()

        assert not stale_file.exists()
        assert (output_dir / "index.html").exists()
