from __future__ import annotations

import logging
from typing import Any

import markdown
import yaml

from .base_processor import ContentProcessor


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
        self.front_matter: dict[str, Any] = {}

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
            markdown_body = raw_content
            self.front_matter = {}
            markdown_body, self.front_matter = self._extract_front_matter(raw_content)

            # The reset() method clears metadata from the previous run
            self._converter.reset()
            html_string = self._converter.convert(markdown_body)
            # Populate metadata if the extension is enabled
            if "meta" in self.extensions:
                self.meta = getattr(self._converter, "Meta", {})
                self.logger.debug("Extracted metadata from Markdown.")
            if self.front_matter:
                self.meta = self._merge_metadata(self.meta, self.front_matter)
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

    def _extract_front_matter(self, raw_content: str) -> tuple[str, dict[str, Any]]:
        if not raw_content.startswith("---"):
            return raw_content, {}

        lines = raw_content.splitlines()
        if len(lines) < 3:
            return raw_content, {}

        end_index = None
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                end_index = index
                break

        if end_index is None:
            return raw_content, {}

        yaml_block = "\n".join(lines[1:end_index])
        body = "\n".join(lines[end_index + 1 :])
        parsed = yaml.safe_load(yaml_block) or {}
        if not isinstance(parsed, dict):
            raise RuntimeError("Markdown front matter must be a YAML mapping.")
        return body, parsed

    def _merge_metadata(
        self, markdown_meta: dict[str, Any], front_matter: dict[str, Any]
    ) -> dict[str, Any]:
        merged = dict(markdown_meta)
        for key, value in front_matter.items():
            merged[key] = value
        return merged
