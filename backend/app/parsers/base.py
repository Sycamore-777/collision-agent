"""Base parser abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.schemas.document import ParsedDocument


@dataclass(slots=True)
class ParserSource:
    """Normalized parser input."""

    source_name: str
    input_type: str
    content_type: str | None = None
    local_path: str | None = None
    source_uri: str | None = None
    text_content: str | None = None
    metadata: dict = field(default_factory=dict)


class ParserAdapter(ABC):
    """Abstract parser adapter."""

    name: str = "base"

    @abstractmethod
    def supports(self, source: ParserSource) -> bool:
        """Return whether this parser can handle the given input."""

    @abstractmethod
    def parse(self, source: ParserSource) -> ParsedDocument:
        """Return a normalized parsed document."""

