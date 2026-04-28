"""Parser tests."""

from __future__ import annotations

import json

from app.parsers.base import ParserSource
from app.parsers.mineru_adapter import MinerUAdapter
from app.parsers.mock_parser import MockParser
from app.parsers.structured_input_parser import StructuredInputParser


def test_structured_parser_parses_json(sample_event_payload: dict) -> None:
    parser = StructuredInputParser()
    source = ParserSource(
        source_name="sample.json",
        input_type="inline",
        text_content=json.dumps(sample_event_payload),
    )

    document = parser.parse(source)

    assert document.doc_type == "conjunction_message"
    assert document.structured_payload["message_id"] == sample_event_payload["message_id"]
    assert any(element.label == "message_id" for element in document.elements)


def test_mock_parser_builds_fallback_payload() -> None:
    parser = MockParser()
    source = ParserSource(
        source_name="warning.pdf",
        input_type="file",
        text_content="message_id: TEST-001\nmiss_distance_m: 1000\ncollision_probability: 0.0002",
    )

    document = parser.parse(source)

    assert document.parser_name == "mock_parser"
    assert document.structured_payload["message_id"] == "TEST-001"
    assert document.confidence_summary.fallback_used is True


def test_mineru_adapter_routes_document_and_falls_back_without_endpoint() -> None:
    parser = MinerUAdapter()
    source = ParserSource(
        source_name="manual.pdf",
        input_type="file",
        text_content="message_id: MINERU-001\nmiss_distance_m: 900",
    )

    document = parser.parse(source)

    assert document.parser_name == "mineru_adapter"
    assert document.confidence_summary.parser_backend == "mineru_adapter"
    assert document.confidence_summary.fallback_used is True
    assert any("MinerU" in note for note in document.confidence_summary.notes)
