from pathlib import Path
from core.page import Page
from core.site import Site
from core.config import Config
from utils.fs_manager import FileSystemManager
from .base_plugin import BasePlugin


class CollectionIndexerPlugin(BasePlugin):
    """
    Generates index pages for configured collections.
    """

    def after_pages_discovered(self, **kwargs) -> None:
        site: Site = kwargs["site"]
        config: Config = kwargs["config"]
        fs_manager: FileSystemManager = kwargs["fs_manager"]

        collections = config.get("collections", {})
        if not isinstance(collections, dict) or not collections:
            return

        output_dir = Path(config.get("output_directory"))
        base_url = str(config.get("base_url", "")).rstrip("/")

        for name, cfg in collections.items():
            if not isinstance(cfg, dict):
                continue

            index_cfg = cfg.get("index", {})
            if not isinstance(index_cfg, dict) or not index_cfg.get("enabled", False):
                continue

            collection_pages = [
                p for p in site.get_pages() if getattr(p, "collection", None) == name
            ]

            list_items = "\n".join(
                f"<li><article><a href='{p.get_root_rel_url()}'>{p.title}</a></article></li>"
                for p in collection_pages
            )
            html_list = f"<ul>{list_items}</ul>"

            index_page = Page(source_filepath="", config=config, fs_manager=fs_manager)
            index_title = index_cfg.get("title", f"{name.title()} Index")
            index_template = index_cfg.get("template", "blog-indexer.html")
            index_page.add_metadata(
                {
                    "template": index_template,
                    "title": [index_title],
                    "type": f"{name}-index",
                }
            )

            index_page.collection = name
            index_page.collection_config = cfg
            index_page.set_title()
            index_page.set_slug()
            index_page.set_page_type(f"{name}-index")
            index_page.set_processed_content(html_list)

            output_path_value = index_cfg.get("output_path")
            if output_path_value:
                output_path = Path(output_path_value)
                if output_path.suffix.lower() != ".html":
                    output_path = output_path / "index.html"
                index_page.set_output_path(output_dir / output_path)
            else:
                index_page.calculate_output_path(
                    output_dir, url_prefix=cfg.get("url_prefix")
                )

            index_page.generate_root_rel_url()
            if base_url:
                index_page.abs_url = f"{base_url}{index_page.root_rel_url}"
            else:
                index_page.abs_url = index_page.root_rel_url

            site.add_page(index_page)
