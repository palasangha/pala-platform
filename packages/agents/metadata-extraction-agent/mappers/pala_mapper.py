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
    def _as_dict(value: Any) -> Dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _as_list(value: Any) -> List[Any]:
        return value if isinstance(value, list) else []

    @staticmethod
    def map_extracted_data(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map extracted data to Pala schema v1.0.0.

        Args:
            extracted_data: Raw extracted metadata from provider

        Returns:
            Pala schema v1.0.0 compatible structure
        """
        mapper = PalaMapper()
        
        # Calculate field-level confidence scores
        overall_confidence = extracted_data.get("confidence", 0.6)
        
        # Build field confidences based on data completeness
        field_confidences = mapper._calculate_field_confidences(extracted_data, overall_confidence)

        return {
            "schema": "pala_metadata",
            "version": PalaMapper.SCHEMA_VERSION,
            "document_metadata": {
                "type": mapper._extract_document_type(extracted_data, field_confidences),
                "date": mapper._extract_document_date(extracted_data, field_confidences),
                "language": extracted_data.get("language", "en"),
            },
            "parties": mapper._extract_parties(extracted_data, field_confidences),
            "places": mapper._extract_places(extracted_data, field_confidences),
            "storage": mapper._extract_storage_location(extracted_data, field_confidences),
            "access": mapper._extract_access_level(extracted_data, field_confidences),
            "content": {
                "summary": mapper._extract_summary(extracted_data, field_confidences),
                "topics": mapper._extract_key_topics(extracted_data, field_confidences),
                "tone_sentiment": mapper._extract_tone_sentiment(extracted_data, field_confidences),
            },
            "quality_metrics": {
                "overall_confidence": overall_confidence,
                "field_confidences": field_confidences,
            },
        }

    @staticmethod
    def _calculate_field_confidences(data: Dict[str, Any], overall_confidence: float) -> Dict[str, float]:
        """Calculate confidence for each extracted field"""
        confidences = {}
        
        # Document type confidence
        doc_type = data.get("document_type")
        confidences["document_type"] = overall_confidence if doc_type and doc_type != "unknown" else 0.4
        
        # Date confidence
        doc_date = data.get("document_date")
        confidences["document_date"] = overall_confidence if doc_date else 0.3
        
        # Summary confidence
        summary = data.get("summary")
        confidences["summary"] = overall_confidence if summary else 0.2
        
        # Topics confidence
        topics = data.get("key_topics")
        confidences["key_topics"] = overall_confidence if (isinstance(topics, list) and len(topics) > 0) else 0.3
        
        # Parties confidence
        parties = data.get("parties", {})
        if isinstance(parties, dict):
            people = PalaMapper._as_list(parties.get("people") or parties.get("People"))
            organizations = PalaMapper._as_list(parties.get("organizations") or parties.get("Organizations"))
            people_count = len(people)
            org_count = len(organizations)
        else:
            people_count = 0
            org_count = 0
        confidences["parties"] = overall_confidence if (people_count > 0 or org_count > 0) else 0.3
        
        # Places confidence
        places = data.get("places")
        confidences["places"] = overall_confidence if (isinstance(places, list) and len(places) > 0) else 0.3
        
        # Tone confidence
        tone = data.get("tone")
        confidences["tone"] = overall_confidence if tone and tone != "neutral" else 0.5
        
        return confidences

    @staticmethod
    def _extract_document_type(data: Dict[str, Any], field_confidences: Dict[str, float]) -> Dict[str, Any]:
        """Extract document type"""
        doc_type = data.get("document_type", "unknown")
        
        # Handle nested structure
        if isinstance(doc_type, dict):
            value = doc_type.get("value", "unknown")
            confidence = doc_type.get("confidence", field_confidences.get("document_type", 0.5))
        else:
            value = doc_type if doc_type else "unknown"
            confidence = field_confidences.get("document_type", 0.5)
        
        return {"value": value, "confidence": confidence}

    @staticmethod
    def _extract_document_date(data: Dict[str, Any], field_confidences: Dict[str, float]) -> Dict[str, Any]:
        """Extract document date"""
        doc_date = data.get("document_date")
        
        # Handle nested structure
        if isinstance(doc_date, dict):
            value = doc_date.get("value")
            confidence = doc_date.get("confidence", field_confidences.get("document_date", 0.5))
        else:
            value = doc_date if doc_date else None
            confidence = field_confidences.get("document_date", 0.5)
        
        return {
            "value": value,
            "confidence": confidence,
            "format": "ISO8601",
        }

    @staticmethod
    def _extract_parties(data: Dict[str, Any], field_confidences: Dict[str, float]) -> Dict[str, Any]:
        """Extract parties (people and organizations)"""
        parties_data = PalaMapper._as_dict(data.get("parties"))
        
        # Try nested structure first (lowercase)
        people = PalaMapper._as_list(parties_data.get("people"))
        organizations = PalaMapper._as_list(parties_data.get("organizations"))
        
        # If nested structure is empty, try Ollama's capitalized structure
        if not people and not organizations:
            people = PalaMapper._as_list(parties_data.get("People"))
            organizations = PalaMapper._as_list(parties_data.get("Organizations"))
        
        # If still empty, try flat structure
        if not people and not organizations:
            people = PalaMapper._as_list(data.get("people"))
            organizations = PalaMapper._as_list(data.get("organizations"))
        
        overall_confidence = field_confidences.get("parties", 0.5)
        
        return {
            "people": [
                {"name": p.get("name"), "role": p.get("role"), "confidence": p.get("confidence", overall_confidence)}
                for p in people if isinstance(p, dict)
            ],
            "organizations": [
                {"name": o.get("name"), "role": o.get("role"), "confidence": o.get("confidence", overall_confidence)}
                for o in organizations if isinstance(o, dict)
            ],
            "overall_confidence": overall_confidence,
        }

    @staticmethod
    def _extract_places(data: Dict[str, Any], field_confidences: Dict[str, float]) -> Dict[str, Any]:
        """Extract places/locations"""
        places_data = data.get("places")
        
        # Handle both nested dict and flat list structures
        if isinstance(places_data, dict):
            locations = PalaMapper._as_list(places_data.get("locations"))
        elif isinstance(places_data, list):
            locations = places_data
        else:
            locations = []
        
        overall_confidence = field_confidences.get("places", 0.5)
        
        return {
            "locations": [
                {"name": loc.get("name"), "role": loc.get("role"), "confidence": loc.get("confidence", overall_confidence)}
                for loc in locations if isinstance(loc, dict)
            ],
            "overall_confidence": overall_confidence,
        }

    @staticmethod
    def _extract_storage_location(data: Dict[str, Any], field_confidences: Dict[str, float]) -> Dict[str, Any]:
        """Extract storage location information"""
        storage_data = PalaMapper._as_dict(data.get("storage_location"))
        return {
            "archive": storage_data.get("archive"),
            "collection": storage_data.get("collection"),
            "box": storage_data.get("box"),
            "folder": storage_data.get("folder"),
            "confidence": storage_data.get("confidence", 0.0),
        }

    @staticmethod
    def _extract_access_level(data: Dict[str, Any], field_confidences: Dict[str, float]) -> Dict[str, Any]:
        """Extract access level information"""
        access_data = PalaMapper._as_dict(data.get("access_level"))
        return {
            "level": access_data.get("value", "public"),
            "reasoning": access_data.get("reasoning", ""),
            "confidence": access_data.get("confidence", 0.0),
        }

    @staticmethod
    def _extract_summary(data: Dict[str, Any], field_confidences: Dict[str, float]) -> Dict[str, Any]:
        """Extract document summary"""
        summary_data = data.get("summary")
        
        # Handle nested structure
        if isinstance(summary_data, dict):
            text = summary_data.get("value", "")
            confidence = summary_data.get("confidence", field_confidences.get("summary", 0.5))
        else:
            text = summary_data if summary_data else ""
            confidence = field_confidences.get("summary", 0.5)
        
        return {"text": text, "confidence": confidence}

    @staticmethod
    def _extract_key_topics(data: Dict[str, Any], field_confidences: Dict[str, float]) -> Dict[str, Any]:
        """Extract key topics"""
        topics_data = data.get("key_topics")
        
        # Handle nested structure
        if isinstance(topics_data, dict):
            topics = topics_data.get("topics", [])
            confidence = topics_data.get("confidence", field_confidences.get("key_topics", 0.5))
        elif isinstance(topics_data, list):
            topics = topics_data
            confidence = field_confidences.get("key_topics", 0.5)
        else:
            topics = []
            confidence = 0.0
        
        return {"topics": topics, "confidence": confidence}

    @staticmethod
    def _extract_tone_sentiment(data: Dict[str, Any], field_confidences: Dict[str, float]) -> Dict[str, Any]:
        """Extract tone and sentiment"""
        tone_data = data.get("tone_sentiment")
        
        # Handle nested structure
        if isinstance(tone_data, dict):
            tone = tone_data.get("tone", "neutral")
            sentiment = tone_data.get("sentiment", "neutral")
            confidence = tone_data.get("confidence", field_confidences.get("tone", 0.5))
        else:
            # Try flat structure
            tone = data.get("tone", "neutral")
            sentiment = data.get("sentiment", "neutral")
            confidence = field_confidences.get("tone", 0.5)
        
        return {
            "tone": tone,
            "sentiment": sentiment,
            "confidence": confidence,
        }
