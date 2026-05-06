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

FIELD_KEY_CANDIDATES = {
    "summary": ("summary", "text", "description", "abstract", "body"),
    "document_date": ("document_date", "date_issued", "published", "issued", "date"),
    "language": ("language", "lang"),
    "people": ("people", "person", "names"),
    "places": ("places", "locations", "location", "spatial_coverage"),
    "topics": ("topics", "topic", "key_topics", "subjects"),
    "organizations": ("organizations", "organization", "institutions", "orgs"),
}

PREFERRED_CONTAINER_KEYS = (
    "content",
    "document",
    "pala_metadata",
    "archipelago_metadata",
    "result",
    "metadata",
    "parties",
    "places",
)


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


def _search_nested_value(value: Any, candidate_keys: tuple[str, ...], depth: int = 0, max_depth: int = 6) -> Any:
    if value is None or depth > max_depth:
        return None

    if isinstance(value, dict):
        for candidate_key in candidate_keys:
            if candidate_key in value and _has_value(value[candidate_key]):
                return value[candidate_key]

        for container_key in PREFERRED_CONTAINER_KEYS:
            if container_key in value:
                found = _search_nested_value(value.get(container_key), candidate_keys, depth + 1, max_depth)
                if _has_value(found):
                    return found

        for nested_value in value.values():
            found = _search_nested_value(nested_value, candidate_keys, depth + 1, max_depth)
            if _has_value(found):
                return found

    if isinstance(value, (list, tuple, set)):
        for nested_value in value:
            found = _search_nested_value(nested_value, candidate_keys, depth + 1, max_depth)
            if _has_value(found):
                return found

    return None


def _field_value(*sources: Any, candidate_keys: tuple[str, ...]) -> Any:
    for source in sources:
        found = _search_nested_value(source, candidate_keys)
        if _has_value(found):
            return found
    return None


def extract_metadata_health(metadata: Dict[str, Any] | None, processed_data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Compute equal-weight completeness for the metadata review fields."""
    metadata = metadata or {}
    processed_data = processed_data or {}

    metadata_sources = (metadata, metadata.get("pala_metadata"), metadata.get("archipelago_metadata"))
    processed_sources = (processed_data, processed_data.get("result") if isinstance(processed_data, dict) else None)

    fields = {
        "summary": _field_value(
            *metadata_sources,
            *processed_sources,
            candidate_keys=FIELD_KEY_CANDIDATES["summary"],
        ),
        "document_date": _field_value(
            *metadata_sources,
            *processed_sources,
            candidate_keys=FIELD_KEY_CANDIDATES["document_date"],
        ),
        "language": _field_value(
            *metadata_sources,
            *processed_sources,
            candidate_keys=FIELD_KEY_CANDIDATES["language"],
        ),
        "people": _field_value(
            *metadata_sources,
            *processed_sources,
            candidate_keys=FIELD_KEY_CANDIDATES["people"],
        ),
        "places": _field_value(
            *metadata_sources,
            *processed_sources,
            candidate_keys=FIELD_KEY_CANDIDATES["places"],
        ),
        "topics": _field_value(
            *metadata_sources,
            *processed_sources,
            candidate_keys=FIELD_KEY_CANDIDATES["topics"],
        ),
        "organizations": _field_value(
            *metadata_sources,
            *processed_sources,
            candidate_keys=FIELD_KEY_CANDIDATES["organizations"],
        ),
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
