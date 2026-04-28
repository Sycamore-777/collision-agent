"""Field normalization and aggregation tests."""

from __future__ import annotations

from datetime import datetime

from app.schemas.event import ConjunctionEvent
from app.services.rules import EventAggregator, canonical_lookup, normalize_float


def test_field_aliases_normalize_inputs_without_judgment() -> None:
    payload = {"pc": "0.002", "object1_norad": "12345"}

    assert normalize_float(canonical_lookup(payload, "collision_probability")) == 0.002
    assert canonical_lookup(payload, "primary_norad_id") == "12345"


def test_event_aggregator_groups_versions() -> None:
    first = ConjunctionEvent(
        event_id="evt-1",
        message_id="m-1",
        conjunction_id="conj-1",
        tca_utc=datetime.fromisoformat("2026-04-24T08:30:00+00:00"),
    )
    second = ConjunctionEvent(
        event_id="evt-2",
        message_id="m-2",
        conjunction_id="conj-1",
        tca_utc=datetime.fromisoformat("2026-04-24T08:35:00+00:00"),
    )

    latest, threads = EventAggregator().aggregate([first, second])

    assert len(latest) == 1
    assert list(threads.values())[0] == ["evt-1", "evt-2"]
