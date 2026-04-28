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
        # Be tolerant of several summary shapes:
        # - {"value": "..."}
        # - {"text": "..."}
        # - plain string
        summary_obj = data.get("summary")
        summary_text = ""
        if isinstance(summary_obj, dict):
            summary_text = summary_obj.get("value") or summary_obj.get("text") or ""
        elif isinstance(summary_obj, str):
            summary_text = summary_obj

        if summary_text:
            title = summary_text.split(".")[0][:200]
            return title.strip()
        return "Historical Document"

    @staticmethod
    def _extract_description(data: Dict[str, Any]) -> str:
        """Extract description"""
        summary_obj = data.get("summary")
        if isinstance(summary_obj, dict):
            return summary_obj.get("value") or summary_obj.get("text") or "No description available"
        if isinstance(summary_obj, str):
            return summary_obj
        return "No description available"

    @staticmethod
    def _extract_subjects(data: Dict[str, Any]) -> List[str]:
        """Extract subjects/topics"""
        # Accept either full key_topics or simple topics list
        kt = data.get("key_topics")
        if isinstance(kt, dict):
            topics = kt.get("topics", [])
        else:
            topics = data.get("topics", []) if isinstance(data.get("topics"), list) else []

        dt = data.get("document_type")
        doc_type = dt.get("value") if isinstance(dt, dict) else (dt or "")
        subjects = list(topics)
        if doc_type:
            subjects.insert(0, doc_type)
        return subjects

    @staticmethod
    def _extract_creators(data: Dict[str, Any]) -> List[str]:
        """Extract creators (senders/authors)"""
        creators = []
        # Parties may be nested under 'parties' or provided at top-level as 'people'
        parties = data.get("parties") if isinstance(data.get("parties"), dict) else {}
        people_list = parties.get("people", []) if parties else data.get("people", [])
        if not isinstance(people_list, list):
            people_list = []
        for person in people_list:
            if isinstance(person, dict) and person.get("role") in ["sender", "author", "creator"]:
                creators.append(person.get("name", "Unknown"))
        return creators

    @staticmethod
    def _extract_contributors(data: Dict[str, Any]) -> List[str]:
        """Extract contributors"""
        contributors = []
        parties = data.get("parties") if isinstance(data.get("parties"), dict) else {}
        people_list = parties.get("people", []) if parties else data.get("people", [])
        if not isinstance(people_list, list):
            people_list = []
        for person in people_list:
            if isinstance(person, dict) and person.get("role") in ["recipient", "mentioned", "signed"]:
                contributors.append(person.get("name", "Unknown"))

        orgs_list = parties.get("organizations", []) if parties else data.get("organizations", [])
        if not isinstance(orgs_list, list):
            orgs_list = []
        for org in orgs_list:
            if isinstance(org, dict) and org.get("role") in ["recipient", "mentioned"]:
                contributors.append(org.get("name", "Unknown"))
        return contributors

    @staticmethod
    def _extract_date_issued(data: Dict[str, Any]) -> Optional[str]:
        """Extract date issued"""
        return data.get("document_date", {}).get("value")

    @staticmethod
    def _extract_date_created(data: Dict[str, Any]) -> Optional[str]:
        """Extract date created"""
        return data.get("document_date", {}).get("value")

    @staticmethod
    def _extract_spatial_coverage(data: Dict[str, Any]) -> List[str]:
        """Extract spatial coverage/places"""
        places = []
        place_data = data.get("places", {})
        for location in place_data.get("locations", []):
            places.append(location.get("name", ""))
        return [p for p in places if p]

    @staticmethod
    def _extract_type(data: Dict[str, Any]) -> str:
        """Extract resource type"""
        doc_type = data.get("document_type", {}).get("value", "text")
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
        access_obj = data.get("access_level")
        if isinstance(access_obj, dict):
            access = access_obj.get("value", "public")
            reasoning = access_obj.get("reasoning", "")
        elif isinstance(access_obj, str):
            access = access_obj
            reasoning = ""
        else:
            access = "public"
            reasoning = ""

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
        access_obj = data.get("access_level")
        if isinstance(access_obj, dict):
            access = access_obj.get("value", "public")
        elif isinstance(access_obj, str):
            access = access_obj
        else:
            access = "public"

        access_rights_map = {
            "public": "http://purl.org/coar/access_right/c_abf2",  # open access
            "restricted": "http://purl.org/coar/access_right/c_16ec",  # restricted access
            "private": "http://purl.org/coar/access_right/c_14cb",  # peer-reviewed
        }

        return access_rights_map.get(access, "http://purl.org/coar/access_right/c_abf2")

    @staticmethod
    def _extract_collection_info(data: Dict[str, Any]) -> Dict[str, str]:
        """Extract collection/storage information"""
        storage = data.get("storage_location", {})
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
