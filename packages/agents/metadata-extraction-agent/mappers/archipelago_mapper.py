"""
Archipelago Commons Metadata Format Mapper

Maps extracted metadata to Archipelago Commons schema for museum/archive integration
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ArchipelagoMapper:
    """Maps extracted metadata to Archipelago Commons schema"""

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
        Map extracted data to Archipelago Commons schema.

        Archipelago Commons is used by museums and archives for standardized metadata.

        Args:
            extracted_data: Raw extracted metadata from provider

        Returns:
            Archipelago Commons compatible structure
        """
        mapper = ArchipelagoMapper()

        return {
            "schema": "archipelago_commons",
            "version": ArchipelagoMapper.SCHEMA_VERSION,
            "title": mapper._extract_title(extracted_data),
            "description": mapper._extract_description(extracted_data),
            "subject": mapper._extract_subjects(extracted_data),
            "creator": mapper._extract_creators(extracted_data),
            "contributor": mapper._extract_contributors(extracted_data),
            "date_issued": mapper._extract_date_issued(extracted_data),
            "date_created": mapper._extract_date_created(extracted_data),
            "spatial_coverage": mapper._extract_spatial_coverage(extracted_data),
            "type": mapper._extract_type(extracted_data),
            "format": "text/plain",
            "language": extracted_data.get("language", "en"),
            "identifier": None,  # Will be set by Archipelago system
            "rights": mapper._extract_rights(extracted_data),
            "access_rights": mapper._extract_access_rights(extracted_data),
            "is_part_of": mapper._extract_collection_info(extracted_data),
            "extent": mapper._extract_extent(extracted_data),
            "source": "metadata_extraction_agent",
            "provenance": mapper._extract_provenance(extracted_data),
            "confidence_metadata": mapper._extract_confidence_metadata(extracted_data),
        }

    @staticmethod
    def _extract_title(data: Dict[str, Any]) -> str:
        """Extract title for Archipelago"""
        summary_data = ArchipelagoMapper._as_dict(data.get("summary"))
        summary = summary_data.get("value", "")
        if summary:
            # Use first sentence or truncate at 200 chars
            title = summary.split(".")[0][:200]
            return title.strip()
        return "Historical Document"

    @staticmethod
    def _extract_description(data: Dict[str, Any]) -> str:
        """Extract description"""
        summary_data = ArchipelagoMapper._as_dict(data.get("summary"))
        return summary_data.get("value", "No description available")

    @staticmethod
    def _extract_subjects(data: Dict[str, Any]) -> List[str]:
        """Extract subjects/topics"""
        topics_data = ArchipelagoMapper._as_dict(data.get("key_topics"))
        topics = ArchipelagoMapper._as_list(topics_data.get("topics"))
        doc_type_data = ArchipelagoMapper._as_dict(data.get("document_type"))
        doc_type = doc_type_data.get("value", "")
        subjects = list(topics)
        if doc_type:
            subjects.insert(0, doc_type)
        return subjects

    @staticmethod
    def _extract_creators(data: Dict[str, Any]) -> List[str]:
        """Extract creators (senders/authors)"""
        creators = []
        parties = ArchipelagoMapper._as_dict(data.get("parties"))
        for person in ArchipelagoMapper._as_list(parties.get("people")):
            if not isinstance(person, dict):
                continue
            if person.get("role") in ["sender", "author", "creator"]:
                creators.append(person.get("name", "Unknown"))
        return creators

    @staticmethod
    def _extract_contributors(data: Dict[str, Any]) -> List[str]:
        """Extract contributors"""
        contributors = []
        parties = ArchipelagoMapper._as_dict(data.get("parties"))
        for person in ArchipelagoMapper._as_list(parties.get("people")):
            if not isinstance(person, dict):
                continue
            if person.get("role") in ["recipient", "mentioned", "signed"]:
                contributors.append(person.get("name", "Unknown"))
        for org in ArchipelagoMapper._as_list(parties.get("organizations")):
            if not isinstance(org, dict):
                continue
            if org.get("role") in ["recipient", "mentioned"]:
                contributors.append(org.get("name", "Unknown"))
        return contributors

    @staticmethod
    def _extract_date_issued(data: Dict[str, Any]) -> Optional[str]:
        """Extract date issued"""
        document_date = ArchipelagoMapper._as_dict(data.get("document_date"))
        return document_date.get("value")

    @staticmethod
    def _extract_date_created(data: Dict[str, Any]) -> Optional[str]:
        """Extract date created"""
        document_date = ArchipelagoMapper._as_dict(data.get("document_date"))
        return document_date.get("value")

    @staticmethod
    def _extract_spatial_coverage(data: Dict[str, Any]) -> List[str]:
        """Extract spatial coverage/places"""
        places = []
        place_data = ArchipelagoMapper._as_dict(data.get("places"))
        for location in ArchipelagoMapper._as_list(place_data.get("locations")):
            if not isinstance(location, dict):
                continue
            places.append(location.get("name", ""))
        return [p for p in places if p]

    @staticmethod
    def _extract_type(data: Dict[str, Any]) -> str:
        """Extract resource type"""
        document_type = ArchipelagoMapper._as_dict(data.get("document_type"))
        doc_type = document_type.get("value", "text")
        type_mapping = {
            "letter": "letter",
            "memo": "memo",
            "telegram": "telegram",
            "fax": "fax",
            "email": "email",
            "invitation": "invitation",
            "form": "form",
            "contract": "contract",
            "report": "report",
        }
        return type_mapping.get(doc_type, "text")

    @staticmethod
    def _extract_rights(data: Dict[str, Any]) -> str:
        """Extract rights information"""
        access_level = ArchipelagoMapper._as_dict(data.get("access_level"))
        access = access_level.get("value", "public")
        reasoning = access_level.get("reasoning", "")

        rights_map = {
            "public": "Public Domain / Open Access",
            "restricted": "Restricted Access",
            "private": "Private Access",
        }

        base_rights = rights_map.get(access, "Unknown")
        if reasoning:
            return f"{base_rights}: {reasoning}"
        return base_rights

    @staticmethod
    def _extract_access_rights(data: Dict[str, Any]) -> str:
        """Extract access rights URI (COAR standard)"""
        access_level = ArchipelagoMapper._as_dict(data.get("access_level"))
        access = access_level.get("value", "public")

        access_rights_map = {
            "public": "http://purl.org/coar/access_right/c_abf2",  # open access
            "restricted": "http://purl.org/coar/access_right/c_16ec",  # restricted access
            "private": "http://purl.org/coar/access_right/c_14cb",  # peer-reviewed
        }

        return access_rights_map.get(access, "http://purl.org/coar/access_right/c_abf2")

    @staticmethod
    def _extract_collection_info(data: Dict[str, Any]) -> Dict[str, str]:
        """Extract collection/storage information"""
        storage = ArchipelagoMapper._as_dict(data.get("storage_location"))
        return {
            "archive": storage.get("archive", ""),
            "collection": storage.get("collection", ""),
            "box": storage.get("box", ""),
            "folder": storage.get("folder", ""),
        }

    @staticmethod
    def _extract_extent(data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract extent information"""
        return {
            "text_length_chars": data.get("input_text_length", 0),
        }

    @staticmethod
    def _extract_provenance(data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract provenance information"""
        return {
            "extraction_method": "metadata_extraction_agent",
            "extraction_timestamp": data.get("extraction_timestamp"),
            "provider_model": data.get("model", "unknown"),
            "document_context": data.get("document_context", ""),
        }

    @staticmethod
    def _extract_confidence_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract confidence/quality metadata"""
        confidences = {}
        for field, value in data.items():
            if isinstance(value, dict) and "confidence" in value:
                confidences[field] = value["confidence"]

        overall_confidence = (
            sum(confidences.values()) / len(confidences) if confidences else 0.0
        )

        return {
            "overall_confidence": round(overall_confidence, 3),
            "field_confidences": confidences,
            "confidence_threshold": 0.75,  # Archipelago standard
            "high_confidence_fields": [
                field for field, conf in confidences.items() if conf >= 0.75
            ],
            "low_confidence_fields": [
                field for field, conf in confidences.items() if conf < 0.5
            ],
        }
