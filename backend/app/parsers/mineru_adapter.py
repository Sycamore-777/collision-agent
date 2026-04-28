"""MinerU adapter with graceful fallback to mock parsing."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import httpx

from app.core.config import get_settings
from app.parsers.base import ParserAdapter, ParserSource
from app.parsers.mock_parser import MockParser
from app.schemas.document import ConfidenceSummary, DocumentElement, ParsedDocument


class MinerUAdapter(ParserAdapter):
    """Parse PDF/DOCX/PPTX through a configured MinerU-compatible service."""

    name = "mineru_adapter"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.mock_parser = MockParser()

    def supports(self, source: ParserSource) -> bool:
        return source.source_name.lower().endswith((".pdf", ".docx", ".pptx"))

    def parse(self, source: ParserSource) -> ParsedDocument:
        if self.settings.parser_backend != "mineru" or not self.settings.mineru_base_url:
            return self._fallback(source, "MinerU is not configured; mock fallback used.")

        if not source.local_path or not Path(source.local_path).exists():
            return self._fallback(source, "MinerU requires a local file path; mock fallback used.")

        try:
            payload = self._call_mineru(source)
            return self._normalize_payload(source, payload)
        except Exception as exc:
            return self._fallback(source, f"MinerU call failed: {exc}; mock fallback used.")

    def _call_mineru(self, source: ParserSource) -> dict:
        headers = {}
        if self.settings.mineru_api_key:
            headers["Authorization"] = f"Bearer {self.settings.mineru_api_key}"

        endpoint = f"{self.settings.mineru_base_url.rstrip('/')}/parse"
        path = Path(source.local_path or "")
        with path.open("rb") as file_obj:
            response = httpx.post(
                endpoint,
                headers=headers,
                files={"file": (source.source_name, file_obj, source.content_type or "application/octet-stream")},
                timeout=self.settings.mineru_timeout,
            )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("MinerU response must be a JSON object")
        return data

    def _normalize_payload(self, source: ParserSource, payload: dict) -> ParsedDocument:
        raw_elements = payload.get("elements") or payload.get("blocks") or []
        elements: list[DocumentElement] = []

        if isinstance(raw_elements, list):
            for index, item in enumerate(raw_elements):
                if not isinstance(item, dict):
                    continue
                text = str(item.get("text") or item.get("content") or "").strip()
                if not text:
                    continue
                raw_value = item.get("value")
                value = raw_value if isinstance(raw_value, (str, int, float, bool)) else text
                elements.append(
                    DocumentElement(
                        element_id=str(item.get("element_id") or f"mineru-{index + 1}"),
                        page=item.get("page") if isinstance(item.get("page"), int) else None,
                        kind=str(item.get("kind") or item.get("type") or "text"),
                        label=str(item.get("label") or "text"),
                        text=text,
                        value=value,
                        confidence=float(item.get("confidence") or 0.85),
                    )
                )

        if not elements:
            text = str(payload.get("markdown") or payload.get("text") or payload.get("content") or "").strip()
            if text:
                for index, line in enumerate([line.strip() for line in text.splitlines() if line.strip()]):
                    elements.append(
                        DocumentElement(
                            element_id=f"mineru-text-{index + 1}",
                            kind="text",
                            label="text",
                            text=line,
                            value=line,
                            confidence=0.8,
                        )
                    )

        if not elements:
            return self._fallback(source, "MinerU response contained no text elements; mock fallback used.")

        return ParsedDocument(
            doc_id=str(payload.get("doc_id") or uuid4()),
            doc_type=str(payload.get("doc_type") or "mineru_document"),
            source=source.source_name,
            parser_name=self.name,
            elements=elements,
            confidence_summary=ConfidenceSummary(
                overall=float(payload.get("confidence") or 0.85),
                parser_backend=self.name,
                fallback_used=False,
                notes=["MinerU parsed document successfully."],
            ),
            structured_payload=payload.get("structured_payload") if isinstance(payload.get("structured_payload"), dict) else {},
            metadata={"mineru_payload_keys": sorted(payload.keys())},
        )

    def _fallback(self, source: ParserSource, note: str) -> ParsedDocument:
        document = self.mock_parser.parse(source)
        document.parser_name = self.name
        document.confidence_summary.parser_backend = self.name
        document.confidence_summary.fallback_used = True
        document.confidence_summary.notes = document.confidence_summary.notes + [note]
        return document
