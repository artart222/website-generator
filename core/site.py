from .config import Config
from utils.fs_manager import FileSystemManager
from .page import Page


"""
* **`Site`**
    * **Responsibility:** Represents the website to be generated. Contains all pages, assets, and site-wide metadata.
    * **Attributes:**
        * `name: str` - Name of the site.
        * `base_url: str` - Base URL for the site (used for absolute links).
        * `pages: list[Page]` - Collection of all pages in the site.
        * `config: Configuration` - Reference to the project configuration.
    * **Methods:**
        * `add_page(page: Page)`
"""


class Site:
    def __init__(self, config) -> None:
        self.name: str = ""
        self.base_url: str = ""
        self.pages: list[Page] = []
        self.config: Config = config

    def add_page(self, page: Page):
        self.pages.append(page)

    def discover_content(self, source_dir: str, pages_dir_name: str):
        fs_manager = FileSystemManager()
        pages = fs_manager.list_files(self.config.get("source_directory"))
        for page in pages:
            self.add_page(Page(page))
        return self.pages

    def get_site_pages(self) -> list[Page]:
        return self.pages
