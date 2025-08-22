from processor.base_processor import ContentProcessor
from utils.fs_manager import FileSystemManager
import logging

"""
* **`Page`**
    * **Responsibility:** Represents a single page in the website.
    * **Attributes:**
        * `title: str`
        * `slug: str` - URL-friendly identifier (e.g., "about-us").
        * `metadata: dict` - Frontmatter or other page-specific data.
        * `raw_content: str` - The raw content read from the source file.
        * `processed_content: str` - Content after processing (e.g., Markdown to HTML).
    * **Methods:**
        * `__init__(source_filepath: str, config: Configuration, parent_site: Site)`
        * `load_content_and_metadata()`: Reads the source file, parses frontmatter/metadata.
        * `process_content(content_processor: ContentProcessor | None)`: Converts raw content (e.g., Markdown to HTML).
        * `render(template_engine: TemplateEngine, global_data: dict) -> str`: Renders the page to an HTML string.
        * `get_context() -> dict`: Prepares the data context for template rendering.
        * `calculate_output_path(output_dir: str)`
"""


class Page:
    def __init__(self, source_filepath) -> None:
        self.logger = logging.getLogger(__name__)
        self.title = ""
        self.source_filepath: str = source_filepath
        self.metadata = {}
        self.processed_content = ""
        self.raw_content = ""
        self.slug = ""
        self.page_type = [None]

    def read_source_file(self):
        local_fs_manager = FileSystemManager()
        self.raw_content = local_fs_manager.read_file(self.source_filepath)

    def process_content(self, content_processor: ContentProcessor | None):
        if content_processor is not None:
            self.processed_content = content_processor.process(self.raw_content)
        else:
            self.processed_content = self.raw_content
            print("No content was given for this page")  # TODO: Refine this.

    def process_metadata(self, content_processor: ContentProcessor | None):
        if content_processor is not None:
            self.metadata = content_processor.get_metadata()
        else:
            self.metadata = {}
            print(
                "No content processor provided for metadata extraction"
            )  # TODO: Refine this.

        title_value = self.metadata.get("title")
        # TODO: Refine this section
        if title_value:
            if isinstance(title_value, list) and len(title_value) > 1:
                print("Warning there is more than 1 title for this page")
                print("Concatenating all titles and giving them as title")
                output = ""
                for title in title_value:
                    output = output + " " + str(title)
                self.title = output.strip()
            elif isinstance(title_value, list) and len(title_value) == 1:
                self.title = str(title_value[0])
            else:
                print("No title was has been found")

    def get_contex(self) -> str:
        return self.processed_content

    def get_title(self) -> str:
        return self.title

    def get_metadata(self) -> dict:
        return self.metadata

    def get_page_type(self):
        return self.page_type

    # TODO: I don't know if this is good idea
    def set_slug(self):
        if self.metadata.get("slug"):
            self.slug = self.metadata.get("slug")
        elif self.metadata.get("title"):
            self.slug = self.metadata.get("title")

    # TODO: I don't know if this is good idea
    def set_page_type(self):
        if self.metadata.get("type"):
            self.page_type = self.metadata.get("type")

    def get_source_filepath(self):
        return self.source_filepath
