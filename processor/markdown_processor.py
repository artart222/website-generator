from .base_processor import ContentProcessor
import markdown
import sys


class MarkdownProcessor(ContentProcessor):
    """
    Processes content written in Markdown format and converts it to HTML.
    """

    def __init__(self, extensions: list[str] | None = None):
        """
        Initializes the MarkdownProcessor.

        Args:
            extensions: Optional list of Markdown extensions to use
                        (e.g., ['fenced_code', 'tables']).
        """
        self.extensions = extensions if extensions is not None else []
        self.meta = {}
        # You can also initialize the Markdown converter instance here
        # if you want to reuse it with specific configurations.
        # self.md_converter = markdown.Markdown(extensions=self.extensions)

    def process(self, raw_content: str) -> str:
        """
        Converts a raw Markdown string into an HTML string.

        Args:
            raw_content: The string containing Markdown text.

        Returns:
            A string containing the equivalent HTML.
        """
        try:
            markdown_converter = markdown.Markdown(extensions=self.extensions)
            html_string = markdown_converter.convert(raw_content)
            if "meta" in self.extensions:
                self.meta = getattr(markdown_converter, "Meta", {})
            return html_string
        except Exception as e:
            print(
                "There was an error in process method in MarkdownProcessor class returning raw_content"
            )
            print(e, file=sys.stderr)
            return raw_content

    def get_metadata(self) -> dict:
        if "meta" in self.extensions:
            return self.meta
        else:
            print('"meta" is not in extensions. returning empty dictianry')
            return {}
