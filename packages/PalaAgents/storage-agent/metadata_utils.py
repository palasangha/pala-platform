"""Helpers for metadata completeness scoring and updates."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


REVIEW_FIELDS = [
    "summary",
    "document_date",
    "language",
    "people",
    "places",
    "topics",
    "organizations",
]


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set)):
        return any(_has_value(item) for item in value)
    if isinstance(value, dict):
        return any(_has_value(item) for item in value.values())
    return True


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if _has_value(value):
            return value
    return None


def extract_metadata_health(metadata: Dict[str, Any] | None, processed_data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Compute equal-weight completeness for the metadata review fields."""
    metadata = metadata or {}
    processed_data = processed_data or {}

    content = metadata.get("content") if isinstance(metadata.get("content"), dict) else {}
    document = metadata.get("document") if isinstance(metadata.get("document"), dict) else {}
    document_date = metadata.get("date") if not isinstance(metadata.get("date"), dict) else metadata.get("date", {})

    people = _first_non_empty(
        metadata.get("people"),
        (metadata.get("parties", {}) or {}).get("people") if isinstance(metadata.get("parties"), dict) else None,
        content.get("people") if isinstance(content, dict) else None,
        processed_data.get("people"),
    )
    places = _first_non_empty(
        metadata.get("places"),
        metadata.get("locations"),
        (metadata.get("places", {}) or {}).get("locations") if isinstance(metadata.get("places"), dict) else None,
        content.get("places") if isinstance(content, dict) else None,
        processed_data.get("locations"),
    )
    topics = _first_non_empty(
        metadata.get("topics"),
        content.get("topics") if isinstance(content, dict) else None,
        processed_data.get("topics"),
    )
    organizations = _first_non_empty(
        metadata.get("organizations"),
        (metadata.get("parties", {}) or {}).get("organizations") if isinstance(metadata.get("parties"), dict) else None,
        content.get("organizations") if isinstance(content, dict) else None,
        processed_data.get("organizations"),
    )

    fields = {
        "summary": _first_non_empty(
            metadata.get("summary"),
            content.get("summary"),
            document.get("summary") if isinstance(document, dict) else None,
            processed_data.get("summary"),
            processed_data.get("text"),
        ),
        "document_date": _first_non_empty(
            document.get("date", {}).get("value") if isinstance(document.get("date"), dict) else None,
            document_date.get("value") if isinstance(document_date, dict) else None,
            metadata.get("document_date"),
            metadata.get("date"),
            processed_data.get("date"),
        ),
        "language": _first_non_empty(
            metadata.get("language"),
            content.get("language") if isinstance(content, dict) else None,
            processed_data.get("language"),
        ),
        "people": people,
        "places": places,
        "topics": topics,
        "organizations": organizations,
    }

    present_fields = [name for name, value in fields.items() if _has_value(value)]
    missing_fields = [name for name in REVIEW_FIELDS if name not in present_fields]
    score = round((len(present_fields) / len(REVIEW_FIELDS)) * 100, 2) if REVIEW_FIELDS else 0.0

    return {
        "score": score,
        "present_fields": present_fields,
        "missing_fields": missing_fields,
        "field_values": fields,
    }


def deep_merge_dict(existing: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge metadata patch into existing metadata."""
    merged = deepcopy(existing or {})
    patch = patch or {}

    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge_dict(merged[key], value)
        else:
            merged[key] = deepcopy(value)

    return merged
