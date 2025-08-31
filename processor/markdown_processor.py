from .base_processor import ContentProcessor
import markdown
import logging


class MarkdownProcessor(ContentProcessor):
    """
    Processes content written in Markdown format and converts it to HTML.
    """

    def __init__(self, extensions: list[str] | None = None) -> None:
        """
        Initializes the MarkdownProcessor.

        Args:
            extensions: Optional list of Markdown extensions to use
                        (e.g., ['fenced_code', 'tables']).
        """
        self.logger = logging.getLogger(__name__)
        self.extensions = extensions if extensions is not None else []
        self._converter = markdown.Markdown(extensions=self.extensions)
        self.meta = {}

    def process(self, raw_content: str) -> str:
        """
        Converts a raw Markdown string into an HTML string and extracts metadata
        if the meta extension is enabled.

        Args:
            raw_content: The string containing Markdown text.

        Returns:
            A string containing the equivalent HTML.

        Raises:
            ImportError: If there extension doesn't been found.
            RuntimeError: For other errors.
        """
        self.logger.debug("Converting Markdown to HTML.")
        try:
            # The reset() method clears metadata from the previous run
            self._converter.reset()
            html_string = self._converter.convert(raw_content)
            # Populate metadata if the extension is enabled
            if "meta" in self.extensions:
                self.meta = getattr(self._converter, "Meta", {})
                self.logger.debug("Extracted metadata from Markdown.")
            return html_string
        except ImportError as e:
            msg = "Markdown extension not found"
            self.logger.error(msg)
            raise ImportError(msg) from e
        except Exception as e:
            msg = "An unexpected error occurred during Markdown processing"
            self.logger.error(msg)
            raise RuntimeError(msg) from e

    def get_metadata(self) -> dict:
        """
        Returns the metadata extracted from the last processed content.
        """
        if "meta" not in self.extensions:
            self.logger.warning(
                "get_metadata() called, but 'meta' extension is not enabled. Returning empty dictionary."
            )
        return self.meta
