"""Parser selection logic."""

from __future__ import annotations

from app.parsers.base import ParserAdapter, ParserSource
from app.parsers.mineru_adapter import MinerUAdapter
from app.parsers.mock_parser import MockParser
from app.parsers.structured_input_parser import StructuredInputParser


class ParserRegistry:
    """Resolve the best parser for an input source."""

    def __init__(self) -> None:
        self.adapters: list[ParserAdapter] = [
            StructuredInputParser(),
            MinerUAdapter(),
            MockParser(),
        ]

    def resolve(self, source: ParserSource) -> ParserAdapter:
        for adapter in self.adapters:
            if adapter.supports(source):
                return adapter
        return MockParser()

