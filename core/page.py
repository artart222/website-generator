import logging
import os
from slugify import slugify
from processor.base_processor import ContentProcessor
from utils.fs_manager import FileSystemManager
from .config import Config
from typing import Optional, Any


class Page:
    """Represents a single page in the website."""

    def __init__(
        self,
        source_filepath,
        config: Config,
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
        self.config: Config = config
        self.source_filepath: str = source_filepath
        self.fs_manager: FileSystemManager | None = fs_manager

        # Attributes to be populated by loading methods
        self.raw_content: str = ""
        self.processed_content: str = ""
        self.metadata: dict = {}
        self.title: str = ""
        self.slug: str = ""
        self.page_type: str | None = None

        self.output_path: str = ""
        self.url: str = ""

    # TODO:
    # Will be DEPRECATED.
    # Instead load method will be used.
    def read_source_file(self) -> None:
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
    def process_content(self, content_processor: ContentProcessor | None) -> None:
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
    def process_metadata(self, content_processor: ContentProcessor | None) -> None:
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

    def load(self, content_processor: ContentProcessor | None) -> None:
        """
        Reads, processes, and extracts all data for the page from its source file.

        Args:
            content_processor: An optional processor for content and metadata.
        """
        self.logger.debug(f"Loading page from: {self.source_filepath}")
        if self.fs_manager is not None:
            self.raw_content = self.fs_manager.read_file(self.source_filepath)
        else:
            self.logger.error(
                "FileSystemManager is not provided. Cannot read source file."
            )
            self.raw_content = ""

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

    def generate_url(self) -> str:
        """
        Generates the URL for the page based on slug and page type.

        Args:
            base_url (str, optional): The base URL of the website (e.g., "https://example.com").
                                    If not provided, returns a relative URL.

        Returns:
            str: The page URL.
        """
        base_url = self.config.get("base_url", "") if self.config is not None else ""
        # Build relative path
        parts = []
        if self.page_type:
            parts.append(self.page_type)
        parts.append(self.slug)
        relative_path = "/".join(parts) + "/"

        # Combine with base URL if provided
        if base_url:
            # Ensure base_url doesn't end with '/'
            base_url = base_url.rstrip("/")
            self.url = f"{base_url}/{relative_path}"
        else:
            self.url = f"/{relative_path}"

        return self.url

    def _populate_attributes(self) -> None:
        """Internal helper method to set page attributes based on extracted metadata."""
        default_title = os.path.splitext(os.path.basename(self.source_filepath))[0]
        self.title = str(self.metadata.get("title", [default_title])[0])

        slug_source = str(self.metadata.get("slug", [self.title])[0])
        self.slug = slugify(slug_source)

        # TODO: In future change page_type to list of types
        # Not a list with a type.
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
        if not self.fs_manager:
            raise RuntimeError("FileSystemManager is required to create output paths")

        # Build slugified folder path
        parts = [output_dir]
        if self.page_type:
            parts.append(slugify(self.page_type))
        parts.append(slugify(self.slug))

        folder_path = os.path.join(*parts)

        # Ensure folder exists via fs_manager
        self.fs_manager.create_directory(folder_path)

        # Set output path to 'index.html' inside folder
        self.output_path = os.path.join(folder_path, "index.html")
        return self.output_path

    def set_raw_content(self, content: str) -> None:
        """Sets the page raw content.

        Args:
            content: Input content which will be set for raw_content.
        """
        self.raw_content = content

    def set_processed_content(self, content: str) -> None:
        """Sets the page processed content.

        Args:
            content: Input content which will be set for processed_content.
        """
        self.processed_content = content

    def add_metadata(self, inp: dict[str, Any]) -> None:
        """
        Adds a metadata to page metadadas.

        Args:
            inp: a dictionary which it's items will be added to metadata.
        """
        self.metadata.update(inp)

    def set_slug(self) -> None:
        """Sets the page slug based on metadata or title."""
        slug_source = self.metadata.get("slug", [self.title])[0]
        self.slug = slugify(str(slug_source))

    def set_page_type(self, page_type: str) -> None:
        """
        Sets the page type based on input.

        Args:
            page_type: The page type which user want to set.
        """
        self.page_type = page_type

    def set_output_path(self, output_path: str) -> None:
        """Sets the output path for the page."""
        self.output_path = output_path

    def get_context(self, header: str) -> dict:
        """
        Returns the context dictionary to be passed to templates.

        Returns:
            Context which have at least `content` and `page_title`.
        """
        return {
            "content": self.processed_content,
            "page_title": self.get_title(),
            "header": header,
            "site_name": self.config.get("site_name", "Default Site Name"),
        }

    def get_title(self) -> str:
        """
        Returns the page title.

        Returns:
            The page title.
        """
        return self.title

    def get_metadata(self) -> dict:
        """
        Returns the page metadata dictionary.

        Returns:
            The page metadata.
        """
        return self.metadata

    def get_page_type(self) -> list:
        """
        Returns the page type as a list.

        Returns:
            List containing the page type, or empty if None.
        """
        if isinstance(self.page_type, list):
            return self.page_type
        elif self.page_type is None:
            return []
        else:
            return [self.page_type]

    def get_source_filepath(self) -> str:
        """
        Returns the source file path of the page.

        Returns:
            The path to source file.
        """
        return self.source_filepath

    def get_slug(self) -> str:
        """
        Returns the page slug.

        Returns:
            The page slug.
        """
        return self.slug

    def get_output_path(self) -> str:
        """
        Returns the output path of the rendered HTML file.

        Returns:
            The path to output file.
        """
        return self.output_path

    def get_url(self) -> str:
        """
        Returns the URL of HTML file.

        Returns:
            The URL of HTML file.
        """
        return self.url

    def __repr__(self) -> str:
        return f"<Page title='{self.title}' slug='{self.slug}' type='{self.page_type}'>"
