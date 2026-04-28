"""Extract canonical collision events from normalized documents."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from app.schemas.document import ParsedDocument
from app.schemas.event import ConjunctionEvent, EvidenceRef
from app.services.rules import canonical_lookup, normalize_bool, normalize_datetime, normalize_float


def _normalize_label(label: str) -> str:
    return label.lower().replace(" ", "_")


class ConjunctionExtractor:
    """Convert parsed documents into canonical event and constraint objects."""

    event_fields = [
        "message_id",
        "conjunction_id",
        "primary_object_name",
        "secondary_object_name",
        "primary_norad_id",
        "secondary_norad_id",
        "tca_utc",
        "miss_distance_m",
        "relative_speed_mps",
        "collision_probability",
        "reference_frame",
        "covariance_present",
    ]

    def extract_events(self, parsed_documents: list[ParsedDocument]) -> tuple[list[ConjunctionEvent], list[dict[str, Any]]]:
        events: list[ConjunctionEvent] = []
        constraints: list[dict[str, Any]] = []

        for document in parsed_documents:
            if document.doc_type == "constraint":
                constraints.append(document.structured_payload)
                continue

            payload = document.structured_payload
            event = ConjunctionEvent(
                event_id=str(uuid4()),
                message_id=self._extract_value(payload, document, "message_id"),
                conjunction_id=self._extract_value(payload, document, "conjunction_id"),
                primary_object_name=self._extract_value(payload, document, "primary_object_name"),
                secondary_object_name=self._extract_value(payload, document, "secondary_object_name"),
                primary_norad_id=self._extract_value(payload, document, "primary_norad_id"),
                secondary_norad_id=self._extract_value(payload, document, "secondary_norad_id"),
                tca_utc=normalize_datetime(self._extract_value(payload, document, "tca_utc")),
                miss_distance_m=normalize_float(self._extract_value(payload, document, "miss_distance_m")),
                relative_speed_mps=normalize_float(self._extract_value(payload, document, "relative_speed_mps")),
                collision_probability=normalize_float(self._extract_value(payload, document, "collision_probability")),
                reference_frame=self._extract_value(payload, document, "reference_frame"),
                covariance_present=normalize_bool(self._extract_value(payload, document, "covariance_present")),
                evidence_refs=self._build_evidence(document),
            )
            if not event.message_id and Path(document.source).stem:
                event.message_id = Path(document.source).stem
            if not event.conjunction_id:
                event.conjunction_id = event.message_id
            events.append(event)

        return events, constraints

    def _extract_value(self, payload: dict[str, Any], document: ParsedDocument, field_name: str) -> Any:
        direct = canonical_lookup(payload, field_name)
        if direct is not None:
            return direct

        for element in document.elements:
            label = _normalize_label(element.label)
            if field_name == label.split(".")[-1]:
                return element.value or element.text
        return None

    def _build_evidence(self, document: ParsedDocument) -> list[EvidenceRef]:
        evidence_refs: list[EvidenceRef] = []
        for element in document.elements:
            evidence_refs.append(
                EvidenceRef(
                    doc_id=document.doc_id,
                    page=element.page,
                    element_id=element.element_id,
                    quote=element.text[:300],
                    field_name=_normalize_label(element.label).split(".")[-1],
                )
            )
        return evidence_refs

