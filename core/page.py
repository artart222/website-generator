import logging
import os
from slugify import slugify
from processor.base_processor import ContentProcessor
from utils.fs_manager import FileSystemManager
from .config import Config
from typing import Optional


class Page:
    """Represents a single page in the website."""

    def __init__(
        self,
        source_filepath,
        config: Optional[Config],
        fs_manager: Optional[FileSystemManager],
    ) -> None:
        """
        Initializes a new Page object with its source path and configuration.

        Args:
            source_filepath (str): The path to the page's source file.
            config (Config): A reference to the global configuration object.
            fs_manager (FileSystemManager): An instance of the file system manager.
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.source_filepath = source_filepath
        self.fs_manager = fs_manager

        # Attributes to be populated by loading methods
        self.raw_content: str = ""
        self.processed_content: str = ""
        self.metadata: dict = {}
        self.title: str = ""
        self.slug: str = ""
        self.page_type: str | None = None

        self.output_path = ""

    # TODO:
    # Will be DEPRECATED.
    # Instead load method will be used.
    def read_source_file(self):
        """
        Reads the raw content from the source file using a FileSystemManager.
        """
        self.logger.debug(f"Reading source file: {self.source_filepath}")
        if self.fs_manager is not None:
            self.raw_content = self.fs_manager.read_file(self.source_filepath)
        else:
            self.logger.debug(
                "Reading source file was not succefull because no FileSystemManager has been provided"
            )
            return

    # TODO:
    # Will be DEPRECATED.
    # Instead load method will be used.
    def process_content(self, content_processor: ContentProcessor | None):
        """
        Processes the raw content using the provided content processor.

        If no processor is provided, the raw content is assigned to the
        processed_content attribute without modification.

        Args:
            content_processor (ContentProcessor | None): The processor to use.
        """
        if content_processor:
            self.processed_content = content_processor.process(self.raw_content)
        else:
            self.processed_content = self.raw_content
            self.logger.warning(
                f"No content processor provided for page: {self.source_filepath}"
            )

    # TODO:
    # Will be DEPRECATED.
    # Instead load method will be used.
    def process_metadata(self, content_processor: ContentProcessor | None):
        """
        Extracts metadata using a content processor and sets the page `title`.

        Args:
            content_processor (ContentProcessor | None): The processor that was used.
        """
        if content_processor:
            self.metadata = content_processor.get_metadata()
        else:
            self.metadata = {}
            self.logger.debug(
                f"No metadata processor available for page: {self.source_filepath}"
            )

        title_value = self.metadata.get("title")

        if not title_value:
            self.logger.debug(
                f"No 'title' found in metadata for {self.source_filepath}."
            )
            return

        if isinstance(title_value, list):
            if len(title_value) > 1:
                self.logger.warning(
                    f"Multiple titles found for page '{self.source_filepath}'. Concatenating them."
                )
                self.title = " ".join(map(str, title_value))
            elif len(title_value) == 1:
                self.title = str(title_value[0])
        else:
            # Handle the case where title is not a list
            self.title = str(title_value)

        if not self.title:
            self.logger.debug(
                f"No title was ultimately set from metadata for {self.source_filepath}."
            )

    def load(
        self, fs_manager: FileSystemManager, content_processor: ContentProcessor | None
    ):
        """
        Reads, processes, and extracts all data for the page from its source file.

        Args:
            fs_manager: An instance of the file system manager for file operations.
            content_processor: An optional processor for content and metadata.
        """
        self.logger.debug(f"Loading page from: {self.source_filepath}")
        self.raw_content = fs_manager.read_file(self.source_filepath)

        if content_processor:
            self.processed_content = content_processor.process(self.raw_content)
            self.metadata = content_processor.get_metadata()
            self.logger.info(f"Processed content for: {self.source_filepath}")
        else:
            self.processed_content = self.raw_content
            self.logger.warning(
                f"No content processor provided for: {self.source_filepath}"
            )

        self._populate_attributes()

    def _populate_attributes(self):
        """Internal helper method to set page attributes based on extracted metadata."""
        default_title = os.path.splitext(os.path.basename(self.source_filepath))[0]
        self.title = str(self.metadata.get("title", [default_title])[0])

        slug_source = str(self.metadata.get("slug", [self.title])[0])
        self.slug = slugify(slug_source)

        page_type_value = self.metadata.get("type", [None])[0]
        self.page_type = str(page_type_value) if page_type_value else None

        self.logger.debug(
            f"Final attributes for page '{self.title}': Slug='{self.slug}', Type='{self.page_type}'"
        )

    def calculate_output_path(self, output_dir: str) -> str:
        """
        Determines the final output path for the rendered HTML file.

        Args:
            output_dir (str): The base output directory from the config.

        Returns:
            str: The full path for the output file.
        """
        filename = f"{self.slug}.html"
        if self.page_type:
            self.output_path = os.path.join(output_dir, self.page_type, filename)
            return self.output_path
        self.output_path = os.path.join(output_dir, filename)
        return self.output_path

    def set_raw_content(self, content: str):
        """Sets the page raw content.

        Args:
            content: Input content which will be set for raw_content.
        """
        self.raw_content = content

    def set_processed_content(self, content: str):
        """Sets the page processed content.

        Args:
            content: Input content which will be set for processed_content.
        """
        self.processed_content = content

    # TODO: Complete this
    def add_metadata(self, inp):
        """
        Adds a metadata to page metadadas.

        Args:
            inp: a dictionary which it's items will be added to metadata.
        """
        self.metadata.update(inp)

    def set_slug(self):
        """Sets the page slug from metadata, with a fallback to a slugified title."""
        slug_source = self.metadata.get("slug", [self.title])[0]
        self.slug = slugify(str(slug_source))

    def set_page_type(self):
        """Sets the page type from metadata."""
        page_type_value = self.metadata.get("type", [None])[0]
        self.page_type = str(page_type_value) if page_type_value else None

    def set_output_path(self, output_path):
        self.output_path = output_path

    def get_context(self) -> dict:
        """Gets the processed content of the page."""
        return {"content": self.processed_content, "page_title": self.get_title()}

    def get_title(self) -> str:
        """Gets the title of the page."""
        return self.title

    def get_metadata(self) -> dict:
        """Gets the metadata dictionary of the page."""
        return self.metadata

    def get_page_type(self) -> list:
        """Gets the type of the page, always returning a list."""
        if isinstance(self.page_type, list):
            return self.page_type
        elif self.page_type is None:
            return []
        else:
            return [self.page_type]

    def get_source_filepath(self) -> str:
        """Gets the source file path of the page."""
        return self.source_filepath

    def get_slug(self) -> str:
        """Gets the slug of the page."""
        return self.slug

    def get_output_path(self) -> str:
        """Gets the output path of page file."""
        return self.output_path
