"""Parser protocol for the domain."""

from typing import Protocol

from lke.domain.models.document import ParsedContent
from lke.domain.models.source import DataSource


class Parser(Protocol):
    """Protocol for transforming raw sources into ParsedContent."""

    def parse(self, source: DataSource) -> ParsedContent:
        """Parse a data source and extract structured content."""
        ...
