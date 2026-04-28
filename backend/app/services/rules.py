"""Field mapping and event aggregation helpers."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.schemas.event import ConjunctionEvent


FIELD_ALIASES: dict[str, list[str]] = {
    "message_id": ["message_id", "cdm_id", "messageid"],
    "conjunction_id": ["conjunction_id", "conjunctionid", "event_id", "eventid"],
    "primary_object_name": ["primary_object_name", "primary_name", "object1_name", "satellite1_name"],
    "secondary_object_name": ["secondary_object_name", "secondary_name", "object2_name", "satellite2_name"],
    "primary_norad_id": ["primary_norad_id", "primary_norad", "object1_norad", "sat_1_id"],
    "secondary_norad_id": ["secondary_norad_id", "secondary_norad", "object2_norad", "sat_2_id"],
    "tca_utc": ["tca_utc", "tca", "time_of_closest_approach", "closest_approach_time"],
    "miss_distance_m": ["miss_distance_m", "miss_distance", "miss_distance_meter", "min_range_m"],
    "relative_speed_mps": ["relative_speed_mps", "relative_speed", "closing_speed_mps"],
    "collision_probability": ["collision_probability", "pc", "probability_of_collision"],
    "reference_frame": ["reference_frame", "frame"],
    "covariance_present": ["covariance_present", "covariance_available", "has_covariance"],
}


CONSTRAINT_ALIASES: dict[str, list[str]] = {
    "max_collision_probability": ["max_collision_probability", "max_pc"],
    "max_miss_distance_m": ["max_miss_distance_m", "required_miss_distance_m"],
    "forbidden_risk_levels": ["forbidden_risk_levels"],
}


def canonical_lookup(payload: dict[str, Any], field_name: str) -> Any | None:
    """Search for a canonical field using supported aliases."""

    alias_pool = FIELD_ALIASES.get(field_name, [field_name]) + CONSTRAINT_ALIASES.get(field_name, [])
    lowered = {str(key).lower(): value for key, value in payload.items()}
    for alias in alias_pool:
        if alias.lower() in lowered:
            return lowered[alias.lower()]
    return None


def normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y", "present"}
    return False


def normalize_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    if isinstance(value, str):
        cleaned = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(cleaned)
        except ValueError:
            return None
    return None


def event_group_key(event: ConjunctionEvent) -> str:
    """Return the preferred version grouping key."""

    if event.conjunction_id:
        return f"conjunction:{event.conjunction_id}"

    return "|".join(
        [
            event.message_id or "",
            event.primary_norad_id or event.primary_object_name or "",
            event.secondary_norad_id or event.secondary_object_name or "",
            event.tca_utc.isoformat() if event.tca_utc else "",
        ]
    )


class EventAggregator:
    """Group multiple parsed records that point to the same event thread."""

    def aggregate(self, events: list[ConjunctionEvent]) -> tuple[list[ConjunctionEvent], dict[str, list[str]]]:
        grouped: dict[str, list[ConjunctionEvent]] = defaultdict(list)
        for event in events:
            key = event_group_key(event)
            event.version_group_key = key
            grouped[key].append(event)

        latest_events: list[ConjunctionEvent] = []
        threads: dict[str, list[str]] = {}
        for key, versions in grouped.items():
            sorted_versions = sorted(
                versions,
                key=lambda item: item.tca_utc or datetime.min,
            )
            latest = sorted_versions[-1]
            if not latest.event_id:
                latest.event_id = str(uuid4())
            latest_events.append(latest)
            threads[key] = [item.event_id for item in sorted_versions]

        return latest_events, threads
