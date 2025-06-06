from processor.base_processor import ContentProcessor
from utils.fs_manager import FileSystemManager

"""
* **`Page`**
    * **Responsibility:** Represents a single page in the website.
    * **Attributes:**
        * `title: str`
        * `slug: str` - URL-friendly identifier (e.g., "about-us").
        * `source_filepath: str` - Path to the original content file (e.g., Markdown).
        * `output_filepath: str` - Calculated path for the generated HTML file.
        * `template_name: str | None` - Name of the template to use for rendering this page.
        * `metadata: dict` - Frontmatter or other page-specific data.
        * `raw_content: str` - The raw content read from the source file.
        * `processed_content: str` - Content after processing (e.g., Markdown to HTML).
        * `sections: list[Section]` - (Optional) If page structure is more complex than just main content.
        * `elements: list[Element]` - (Alternative to sections) A flat list of elements if sections are not used.
        * `parent_site: Site` - Reference to the parent site.
    * **Methods:**
        * `__init__(source_filepath: str, config: Configuration, parent_site: Site)`
        * `load_content_and_metadata()`: Reads the source file, parses frontmatter/metadata.
        * `process_content(content_processor: ContentProcessor | None)`: Converts raw content (e.g., Markdown to HTML).
        * `render(template_engine: TemplateEngine, global_data: dict) -> str`: Renders the page to an HTML string.
        * `get_context() -> dict`: Prepares the data context for template rendering.
        * `calculate_output_path(output_dir: str)`
"""


class Page:
    def __init__(self) -> None:
        self.title = ""
        self.metadata = {}
        self.processed_content = ""
        self.raw_content = ""

    def read_source_file(self, source_filepath):
        local_fs_manager = FileSystemManager()
        self.raw_content = local_fs_manager.read_file(source_filepath)

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
