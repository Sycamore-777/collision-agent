"""Schemas representing parsed document structures."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ConfidenceSummary(BaseModel):
    """Parser confidence metadata."""

    overall: float = 0.0
    parser_backend: str = "unknown"
    fallback_used: bool = False
    notes: list[str] = Field(default_factory=list)


class DocumentElement(BaseModel):
    """A normalized document element extracted from any input."""

    element_id: str
    page: int | None = None
    kind: str = "field"
    label: str
    text: str
    value: str | float | int | bool | None = None
    confidence: float = 0.0


class ParsedDocument(BaseModel):
    """Normalized representation of an uploaded or fetched document."""

    doc_id: str
    doc_type: str
    source: str
    parser_name: str
    elements: list[DocumentElement] = Field(default_factory=list)
    confidence_summary: ConfidenceSummary
    structured_payload: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)

