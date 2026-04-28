"""
Pala Metadata Format Mapper

Maps extracted metadata fields to Pala schema v1.0.0
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class PalaMapper:
    """Maps extracted metadata to Pala schema v1.0.0"""

    SCHEMA_VERSION = "1.0.0"

    @staticmethod
    def map_extracted_data(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map extracted data to Pala schema v1.0.0.

        Handles both:
        1. Full schema responses (Claude provider)
        2. Simplified schema responses (Ollama provider)

        Args:
            extracted_data: Raw extracted metadata from provider

        Returns:
            Pala schema v1.0.0 compatible structure
        """
        mapper = PalaMapper()

        # Detect if this is a simplified Ollama response or full schema
        is_simplified = "people" in extracted_data or "organizations" in extracted_data or (
            "document_type" in extracted_data and isinstance(extracted_data.get("document_type"), dict) 
            and "value" in extracted_data["document_type"]
            and "locations" in extracted_data
        )

        if is_simplified:
            # Convert simplified format to full schema first
            extracted_data = mapper._normalize_simplified_schema(extracted_data)

        return {
            "schema": "pala_metadata",
            "version": PalaMapper.SCHEMA_VERSION,
            "document_metadata": {
                "type": mapper._extract_document_type(extracted_data),
                "date": mapper._extract_document_date(extracted_data),
                "language": extracted_data.get("language", "en"),
            },
            "parties": mapper._extract_parties(extracted_data),
            "places": mapper._extract_places(extracted_data),
            "storage": mapper._extract_storage_location(extracted_data),
            "access": mapper._extract_access_level(extracted_data),
            "content": {
                "summary": mapper._extract_summary(extracted_data),
                "topics": mapper._extract_key_topics(extracted_data),
                "tone_sentiment": mapper._extract_tone_sentiment(extracted_data),
            },
            "quality_metrics": {
                "overall_confidence": mapper._calculate_overall_confidence(extracted_data),
                "field_confidences": mapper._extract_field_confidences(extracted_data),
            },
        }

    @staticmethod
    def _normalize_simplified_schema(simplified_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert simplified Ollama schema to full schema format.
        
        Simplified format has:
        - people, organizations, locations as arrays
        - summary as dict with text/confidence
        - tone, sentiment as strings
        
        Full format has:
        - parties.people, parties.organizations
        - places.locations
        - summary, key_topics, tone_sentiment nested in content
        """
        normalized = {}

        # Document type
        if "document_type" in simplified_data:
            normalized["document_type"] = simplified_data["document_type"]
        else:
            normalized["document_type"] = {"value": "unknown", "confidence": 0.0}

        # Document date
        if "document_date" in simplified_data:
            normalized["document_date"] = simplified_data["document_date"]
        else:
            normalized["document_date"] = {"value": None, "confidence": 0.0}

        # Parties
        normalized["parties"] = {
            "people": simplified_data.get("people", []),
            "organizations": simplified_data.get("organizations", []),
            "confidence": max(
                [p.get("confidence", 0) for p in simplified_data.get("people", [])]
                + [o.get("confidence", 0) for o in simplified_data.get("organizations", [])]
                + [0]
            ),
        }

        # Places
        normalized["places"] = {
            "locations": simplified_data.get("locations", []),
            "confidence": max(
                [l.get("confidence", 0) for l in simplified_data.get("locations", [])]
                + [0]
            ),
        }

        # Storage location (not in simplified format)
        normalized["storage_location"] = {
            "archive": None,
            "collection": None,
            "box": None,
            "folder": None,
            "confidence": 0.0,
        }

        # Access level
        access_value = simplified_data.get("access_level", "public")
        normalized["access_level"] = {
            "value": access_value if access_value in ["public", "restricted", "private"] else "public",
            "reasoning": "",
            "confidence": 0.5 if access_value else 0.0,
        }

        # Summary
        summary_data = simplified_data.get("summary", {})
        if isinstance(summary_data, dict):
            # Handle both {text: ..., confidence: ...} and {value: ..., confidence: ...}
            if "text" in summary_data and "value" not in summary_data:
                normalized["summary"] = {
                    "value": summary_data.get("text", ""),
                    "confidence": summary_data.get("confidence", 0.5)
                }
            else:
                normalized["summary"] = summary_data
        else:
            normalized["summary"] = {"value": summary_data, "confidence": 0.5}

        # Key topics
        topics_list = simplified_data.get("topics", [])
        normalized["key_topics"] = {
            "topics": topics_list if isinstance(topics_list, list) else [],
            "confidence": 0.7 if topics_list else 0.0,
        }

        # Tone & sentiment
        normalized["tone_sentiment"] = {
            "tone": simplified_data.get("tone", "neutral"),
            "sentiment": simplified_data.get("sentiment", "neutral"),
            "confidence": 0.6,
        }

        # Language
        normalized["language"] = simplified_data.get("language", "en")

        # Notes
        normalized["notes"] = simplified_data.get("confidence_notes")

        return normalized

    @staticmethod
    def _extract_document_type(data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract document type"""
        doc_type_data = data.get("document_type", {})
        return {"value": doc_type_data.get("value", "unknown"), "confidence": doc_type_data.get("confidence", 0.0)}

    @staticmethod
    def _extract_document_date(data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract document date"""
        date_data = data.get("document_date", {})
        return {
            "value": date_data.get("value"),
            "confidence": date_data.get("confidence", 0.0),
            "format": "ISO8601",
        }

    @staticmethod
    def _extract_parties(data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parties (people and organizations)"""
        parties_data = data.get("parties", {})
        return {
            "people": [
                {"name": p.get("name"), "role": p.get("role"), "confidence": p.get("confidence", 0.0)}
                for p in parties_data.get("people", [])
            ],
            "organizations": [
                {"name": o.get("name"), "role": o.get("role"), "confidence": o.get("confidence", 0.0)}
                for o in parties_data.get("organizations", [])
            ],
            "overall_confidence": parties_data.get("confidence", 0.0),
        }

    @staticmethod
    def _extract_places(data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract places/locations"""
        places_data = data.get("places", {})
        return {
            "locations": [
                {"name": loc.get("name"), "role": loc.get("role"), "confidence": loc.get("confidence", 0.0)}
                for loc in places_data.get("locations", [])
            ],
            "overall_confidence": places_data.get("confidence", 0.0),
        }

    @staticmethod
    def _extract_storage_location(data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract storage location information"""
        storage_data = data.get("storage_location", {})
        return {
            "archive": storage_data.get("archive"),
            "collection": storage_data.get("collection"),
            "box": storage_data.get("box"),
            "folder": storage_data.get("folder"),
            "confidence": storage_data.get("confidence", 0.0),
        }

    @staticmethod
    def _extract_access_level(data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract access level information"""
        access_data = data.get("access_level", {})
        return {
            "level": access_data.get("value", "public"),
            "reasoning": access_data.get("reasoning", ""),
            "confidence": access_data.get("confidence", 0.0),
        }

    @staticmethod
    def _extract_summary(data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract document summary"""
        summary_data = data.get("summary", {})
        return {"text": summary_data.get("value", ""), "confidence": summary_data.get("confidence", 0.0)}

    @staticmethod
    def _extract_key_topics(data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key topics"""
        topics_data = data.get("key_topics", {})
        return {"topics": topics_data.get("topics", []), "confidence": topics_data.get("confidence", 0.0)}

    @staticmethod
    def _extract_tone_sentiment(data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract tone and sentiment"""
        tone_data = data.get("tone_sentiment", {})
        return {
            "tone": tone_data.get("tone", "neutral"),
            "sentiment": tone_data.get("sentiment", "neutral"),
            "confidence": tone_data.get("confidence", 0.0),
        }

    @staticmethod
    def _extract_field_confidences(data: Dict[str, Any]) -> Dict[str, float]:
        """Extract confidence scores by field"""
        confidences = {}
        for field, value in data.items():
            if isinstance(value, dict) and "confidence" in value:
                confidences[field] = value["confidence"]
        return confidences

    @staticmethod
    def _calculate_overall_confidence(data: Dict[str, Any]) -> float:
        """Calculate overall confidence across all fields"""
        confidences = []
        for value in data.values():
            if isinstance(value, dict) and "confidence" in value:
                confidences.append(value["confidence"])
            elif isinstance(value, dict):
                for v in value.values():
                    if isinstance(v, dict) and "confidence" in v:
                        confidences.append(v["confidence"])

        result = sum(confidences) / len(confidences) if confidences else 0.0
        return round(result, 3)
