"""Parser for JSON, XML, KVN, and plain structured text inputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4
from xml.etree import ElementTree as ET

from app.parsers.base import ParserAdapter, ParserSource
from app.schemas.document import ConfidenceSummary, DocumentElement, ParsedDocument


def _flatten_json(payload: Any, prefix: str = "") -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    if isinstance(payload, dict):
        for key, value in payload.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(_flatten_json(value, next_prefix))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            flattened.update(_flatten_json(value, f"{prefix}[{index}]"))
    else:
        flattened[prefix] = payload
    return flattened


class StructuredInputParser(ParserAdapter):
    """Native parser for structured or line-oriented payloads."""

    name = "native_structured_parser"

    def supports(self, source: ParserSource) -> bool:
        suffix = Path(source.source_name).suffix.lower()
        return suffix in {".json", ".xml", ".kvn", ".txt"} or source.input_type in {"inline", "url"}

    def parse(self, source: ParserSource) -> ParsedDocument:
        payload_text = source.text_content
        if payload_text is None and source.local_path:
            payload_text = Path(source.local_path).read_text(encoding="utf-8", errors="ignore")
        payload_text = payload_text or ""

        suffix = Path(source.source_name).suffix.lower()
        structured_payload: dict[str, Any]
        if suffix == ".json" or payload_text.strip().startswith("{"):
            structured_payload = json.loads(payload_text)
        elif suffix == ".xml" or payload_text.strip().startswith("<"):
            structured_payload = self._parse_xml(payload_text)
        else:
            structured_payload = self._parse_key_value_text(payload_text)

        doc_type = "constraint" if "constraint" in source.source_name.lower() else "conjunction_message"
        flattened = _flatten_json(structured_payload)
        elements = [
            DocumentElement(
                element_id=f"elem-{index}",
                page=1,
                label=key,
                text=f"{key}: {value}",
                value=value,
                confidence=0.98,
            )
            for index, (key, value) in enumerate(flattened.items(), start=1)
        ]

        return ParsedDocument(
            doc_id=str(uuid4()),
            doc_type=doc_type,
            source=source.source_name,
            parser_name=self.name,
            elements=elements,
            confidence_summary=ConfidenceSummary(
                overall=0.98,
                parser_backend=self.name,
                fallback_used=False,
                notes=["Parsed with native structured parser."],
            ),
            structured_payload=structured_payload,
            metadata={"source_uri": source.source_uri, **source.metadata},
        )

    def _parse_xml(self, payload_text: str) -> dict[str, Any]:
        root = ET.fromstring(payload_text)
        result: dict[str, Any] = {}
        for node in root.iter():
            if node is root:
                continue
            if node.text and node.text.strip():
                result[node.tag] = node.text.strip()
        return result

    def _parse_key_value_text(self, payload_text: str) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for raw_line in payload_text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, value = line.split(":", 1)
            elif "=" in line:
                key, value = line.split("=", 1)
            else:
                continue
            result[key.strip()] = value.strip()
        return result

