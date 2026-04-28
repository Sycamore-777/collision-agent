"""Fallback parser used for binary documents, demos, and tests."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from app.parsers.base import ParserAdapter, ParserSource
from app.schemas.document import ConfidenceSummary, DocumentElement, ParsedDocument


class MockParser(ParserAdapter):
    """Fallback parser that extracts coarse key-value structure from text-like content."""

    name = "mock_parser"

    def supports(self, source: ParserSource) -> bool:
        return True

    def parse(self, source: ParserSource) -> ParsedDocument:
        text = source.text_content
        if text is None and source.local_path:
            raw_bytes = Path(source.local_path).read_bytes()
            text = raw_bytes.decode("utf-8", errors="ignore")
        text = text or ""

        if text.strip().startswith("{"):
            try:
                structured_payload = json.loads(text)
            except json.JSONDecodeError:
                structured_payload = self._fallback_payload(source, text)
        else:
            structured_payload = self._fallback_payload(source, text)

        elements = [
            DocumentElement(
                element_id=f"mock-{index}",
                page=1,
                label=str(key),
                text=f"{key}: {value}",
                value=value,
                confidence=0.7,
            )
            for index, (key, value) in enumerate(structured_payload.items(), start=1)
        ]

        return ParsedDocument(
            doc_id=str(uuid4()),
            doc_type="constraint" if "constraint" in source.source_name.lower() else "conjunction_message",
            source=source.source_name,
            parser_name=self.name,
            elements=elements,
            confidence_summary=ConfidenceSummary(
                overall=0.7,
                parser_backend=self.name,
                fallback_used=True,
                notes=["Binary or unsupported format parsed through mock fallback."],
            ),
            structured_payload=structured_payload,
            metadata={"source_uri": source.source_uri, "fallback": True, **source.metadata},
        )

    def _fallback_payload(self, source: ParserSource, text: str) -> dict:
        payload: dict[str, str] = {}
        for index, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            if ":" in line:
                key, value = line.split(":", 1)
                payload[key.strip()] = value.strip()
            else:
                payload[f"line_{index}"] = line

        if payload:
            return payload

        base_name = Path(source.source_name).stem.lower()
        return {
            "message_id": f"mock-{base_name}",
            "conjunction_id": f"mock-{base_name}",
            "primary_object_name": "PRIMARY-SAT",
            "secondary_object_name": "SECONDARY-SAT",
            "primary_norad_id": "25544",
            "secondary_norad_id": "43013",
            "tca_utc": "2026-04-23T12:00:00Z",
            "miss_distance_m": 950.0,
            "relative_speed_mps": 14230.0,
            "collision_probability": 0.0002,
            "reference_frame": "RTN",
            "covariance_present": True,
        }

