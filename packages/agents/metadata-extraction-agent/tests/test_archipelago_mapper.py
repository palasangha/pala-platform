"""
Unit tests for ArchipelagoMapper
"""

import pytest
from mappers.archipelago_mapper import ArchipelagoMapper


class TestArchipelagoMapper:
    """Test suite for Archipelago Commons schema mapper"""

    def test_map_extracted_data_complete(self):
        """Test mapping complete extracted data"""
        extracted_data = {
            "document_type": {"value": "letter", "confidence": 0.95},
            "document_date": {"value": "1892-03-15", "confidence": 0.88},
            "parties": {
                "people": [
                    {"name": "John Smith", "role": "sender", "confidence": 0.92},
                    {"name": "Jane Doe", "role": "recipient", "confidence": 0.90},
                ],
                "organizations": [{"name": "Monastery Board", "role": "mentioned", "confidence": 0.85}],
                "confidence": 0.90,
            },
            "places": {
                "locations": [{"name": "London", "role": "origin", "confidence": 0.95}],
                "confidence": 0.95,
            },
            "storage_location": {
                "archive": "Pala Sangha",
                "collection": "Letters",
                "box": "15",
                "folder": "3",
                "confidence": 0.75,
            },
            "access_level": {
                "value": "public",
                "reasoning": "Historical document",
                "confidence": 0.85,
            },
            "summary": {"value": "Letter about monastery administrative matters", "confidence": 0.88},
            "key_topics": {"topics": ["Buddhism", "Administration"], "confidence": 0.82},
            "tone_sentiment": {"tone": "formal", "sentiment": "neutral", "confidence": 0.80},
            "language": "en",
            "extraction_timestamp": "2026-02-23T10:30:00Z",
            "input_text_length": 5420,
            "model": "claude",
            "document_context": "historical_letter",
        }

        result = ArchipelagoMapper.map_extracted_data(extracted_data)

        # Check schema metadata
        assert result["schema"] == "archipelago_commons"
        assert result["version"] == "1.0.0"

        # Check Dublin Core fields
        assert result["title"] == "Letter about monastery administrative matters"
        assert result["description"] == "Letter about monastery administrative matters"
        assert "letter" in result["subject"]
        assert "Buddhism" in result["subject"]
        assert "Administration" in result["subject"]

        # Check creators and contributors
        assert "John Smith" in result["creator"]
        assert "Jane Doe" in result["contributor"]
        assert "Monastery Board" in result["contributor"]

        # Check dates
        assert result["date_issued"] == "1892-03-15"
        assert result["date_created"] == "1892-03-15"

        # Check spatial coverage
        assert "London" in result["spatial_coverage"]

        # Check type and format
        assert result["type"] == "letter"
        assert result["format"] == "text/plain"
        assert result["language"] == "en"

        # Check rights (COAR standard)
        assert "Public Domain" in result["rights"]
        assert result["access_rights"] == "http://purl.org/coar/access_right/c_abf2"

        # Check collection info
        assert result["is_part_of"]["archive"] == "Pala Sangha"
        assert result["is_part_of"]["collection"] == "Letters"
        assert result["is_part_of"]["box"] == "15"
        assert result["is_part_of"]["folder"] == "3"

        # Check provenance
        assert result["source"] == "metadata_extraction_agent"
        assert result["provenance"]["extraction_method"] == "metadata_extraction_agent"
        assert result["provenance"]["provider_model"] == "claude"
        assert result["provenance"]["document_context"] == "historical_letter"

        # Check confidence metadata
        assert result["confidence_metadata"]["overall_confidence"] > 0.0
        assert result["confidence_metadata"]["confidence_threshold"] == 0.75
        assert len(result["confidence_metadata"]["high_confidence_fields"]) > 0
        assert "document_type" in result["confidence_metadata"]["field_confidences"]

    def test_extract_title_from_summary(self):
        """Test title extraction from summary"""
        data = {"summary": {"value": "This is a very long letter about monastery affairs. It discusses many topics."}}
        result = ArchipelagoMapper._extract_title(data)
        assert result == "This is a very long letter about monastery affairs"
        assert len(result) < 200

    def test_extract_title_no_summary(self):
        """Test title extraction with no summary"""
        data = {"summary": {"value": ""}}
        result = ArchipelagoMapper._extract_title(data)
        assert result == "Historical Document"

    def test_extract_subjects_with_document_type(self):
        """Test subject extraction includes document type"""
        data = {
            "key_topics": {"topics": ["Buddhism", "Trade"]},
            "document_type": {"value": "telegram"},
        }
        result = ArchipelagoMapper._extract_subjects(data)
        assert result[0] == "telegram"  # Document type comes first
        assert "Buddhism" in result
        assert "Trade" in result

    def test_extract_creators_from_senders(self):
        """Test creator extraction from sender roles"""
        data = {
            "parties": {
                "people": [
                    {"name": "Alice", "role": "sender"},
                    {"name": "Bob", "role": "recipient"},
                    {"name": "Charlie", "role": "author"},
                ]
            }
        }
        result = ArchipelagoMapper._extract_creators(data)
        assert "Alice" in result
        assert "Charlie" in result
        assert "Bob" not in result

    def test_extract_contributors_from_various_roles(self):
        """Test contributor extraction"""
        data = {
            "parties": {
                "people": [
                    {"name": "Alice", "role": "sender"},
                    {"name": "Bob", "role": "recipient"},
                    {"name": "Charlie", "role": "mentioned"},
                    {"name": "Dave", "role": "signed"},
                ],
                "organizations": [
                    {"name": "Org A", "role": "recipient"},
                    {"name": "Org B", "role": "mentioned"},
                ],
            }
        }
        result = ArchipelagoMapper._extract_contributors(data)
        assert "Bob" in result  # recipient
        assert "Charlie" in result  # mentioned
        assert "Dave" in result  # signed
        assert "Org A" in result
        assert "Org B" in result
        assert "Alice" not in result  # senders are creators, not contributors

    def test_extract_spatial_coverage(self):
        """Test spatial coverage extraction"""
        data = {
            "places": {
                "locations": [
                    {"name": "Paris"},
                    {"name": "Berlin"},
                    {"name": ""},  # Empty should be filtered
                ]
            }
        }
        result = ArchipelagoMapper._extract_spatial_coverage(data)
        assert "Paris" in result
        assert "Berlin" in result
        assert "" not in result
        assert len(result) == 2

    def test_extract_type_mapping(self):
        """Test resource type mapping"""
        test_cases = [
            ("letter", "letter"),
            ("memo", "memo"),
            ("telegram", "telegram"),
            ("unknown_type", "text"),
        ]
        for input_type, expected_type in test_cases:
            data = {"document_type": {"value": input_type}}
            result = ArchipelagoMapper._extract_type(data)
            assert result == expected_type

    def test_extract_rights_public(self):
        """Test rights extraction for public access"""
        data = {"access_level": {"value": "public", "reasoning": "Historical record"}}
        result = ArchipelagoMapper._extract_rights(data)
        assert "Public Domain" in result
        assert "Historical record" in result

    def test_extract_rights_restricted(self):
        """Test rights extraction for restricted access"""
        data = {"access_level": {"value": "restricted", "reasoning": "Personal data"}}
        result = ArchipelagoMapper._extract_rights(data)
        assert "Restricted Access" in result
        assert "Personal data" in result

    def test_extract_rights_private(self):
        """Test rights extraction for private access"""
        data = {"access_level": {"value": "private", "reasoning": ""}}
        result = ArchipelagoMapper._extract_rights(data)
        assert "Private Access" in result

    def test_extract_access_rights_uris(self):
        """Test COAR access rights URI mapping"""
        test_cases = [
            ("public", "http://purl.org/coar/access_right/c_abf2"),
            ("restricted", "http://purl.org/coar/access_right/c_16ec"),
            ("private", "http://purl.org/coar/access_right/c_14cb"),
        ]
        for access_level, expected_uri in test_cases:
            data = {"access_level": {"value": access_level}}
            result = ArchipelagoMapper._extract_access_rights(data)
            assert result == expected_uri

    def test_extract_collection_info(self):
        """Test collection information extraction"""
        data = {
            "storage_location": {
                "archive": "National Archives",
                "collection": "Colonial Records",
                "box": "42",
                "folder": "7",
            }
        }
        result = ArchipelagoMapper._extract_collection_info(data)
        assert result["archive"] == "National Archives"
        assert result["collection"] == "Colonial Records"
        assert result["box"] == "42"
        assert result["folder"] == "7"

    def test_extract_extent(self):
        """Test extent extraction"""
        data = {"input_text_length": 12345}
        result = ArchipelagoMapper._extract_extent(data)
        assert result["text_length_chars"] == 12345

    def test_extract_provenance(self):
        """Test provenance extraction"""
        data = {
            "extraction_timestamp": "2026-02-23T10:30:00Z",
            "model": "claude",
            "document_context": "monastery_record",
        }
        result = ArchipelagoMapper._extract_provenance(data)
        assert result["extraction_method"] == "metadata_extraction_agent"
        assert result["extraction_timestamp"] == "2026-02-23T10:30:00Z"
        assert result["provider_model"] == "claude"
        assert result["document_context"] == "monastery_record"

    def test_extract_confidence_metadata(self):
        """Test confidence metadata extraction"""
        data = {
            "document_type": {"confidence": 0.95},
            "document_date": {"confidence": 0.88},
            "parties": {"confidence": 0.90},
            "places": {"confidence": 0.92},
            "storage_location": {"confidence": 0.65},  # Low confidence
            "access_level": {"confidence": 0.85},
            "summary": {"confidence": 0.88},
            "key_topics": {"confidence": 0.82},
            "tone_sentiment": {"confidence": 0.45},  # Low confidence
        }
        result = ArchipelagoMapper._extract_confidence_metadata(data)

        assert result["overall_confidence"] > 0.7
        assert result["confidence_threshold"] == 0.75

        # Check high confidence fields (>= 0.75)
        assert "document_type" in result["high_confidence_fields"]
        assert "places" in result["high_confidence_fields"]
        assert "storage_location" not in result["high_confidence_fields"]

        # Check low confidence fields (< 0.5)
        assert "tone_sentiment" in result["low_confidence_fields"]
        assert "document_type" not in result["low_confidence_fields"]

        # Check field confidences
        assert result["field_confidences"]["document_type"] == 0.95
        assert result["field_confidences"]["storage_location"] == 0.65

    def test_map_extracted_data_minimal(self):
        """Test mapping with minimal data"""
        extracted_data = {
            "document_type": {"value": "unknown", "confidence": 0.0},
            "document_date": {"value": None, "confidence": 0.0},
            "parties": {"people": [], "organizations": [], "confidence": 0.0},
            "places": {"locations": [], "confidence": 0.0},
            "storage_location": {
                "archive": None,
                "collection": None,
                "box": None,
                "folder": None,
                "confidence": 0.0,
            },
            "access_level": {"value": "public", "reasoning": "", "confidence": 0.0},
            "summary": {"value": "", "confidence": 0.0},
            "key_topics": {"topics": [], "confidence": 0.0},
            "tone_sentiment": {"tone": "neutral", "sentiment": "neutral", "confidence": 0.0},
            "language": "en",
        }

        result = ArchipelagoMapper.map_extracted_data(extracted_data)

        assert result["schema"] == "archipelago_commons"
        assert result["title"] == "Historical Document"
        assert result["creator"] == []
        assert result["spatial_coverage"] == []
        assert result["confidence_metadata"]["overall_confidence"] == 0.0
