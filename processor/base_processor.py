from abc import ABC, abstractmethod


class ContentProcessor(ABC):
    """
    Abstract base class for content processors.
    Defines the interface for transforming raw content.
    """

    @abstractmethod
    def process(self, raw_content: str) -> str:
        """
        Processes the raw input string and returns the transformed string.
        For example, converts Markdown/TXT to HTML.

        Args:
            raw_content: The raw string content to process.

        Returns:
            The processed string content.
        """
        pass

    @abstractmethod
    def get_metadata(self) -> dict:
        """
        Returns metadata extracted from the content, if any.
        """
        pass
