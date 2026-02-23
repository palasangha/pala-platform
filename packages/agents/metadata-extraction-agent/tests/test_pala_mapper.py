"""
Unit tests for PalaMapper
"""

import pytest
from mappers.pala_mapper import PalaMapper


class TestPalaMapper:
    """Test suite for Pala schema mapper"""

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
                "locations": [
                    {"name": "London", "role": "origin", "confidence": 0.95},
                    {"name": "Paris", "role": "destination", "confidence": 0.88},
                ],
                "confidence": 0.92,
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
                "reasoning": "Historical document, no sensitive info",
                "confidence": 0.85,
            },
            "summary": {"value": "Letter about monastery matters", "confidence": 0.88},
            "key_topics": {"topics": ["Buddhism", "Administration", "Correspondence"], "confidence": 0.82},
            "tone_sentiment": {"tone": "formal", "sentiment": "neutral", "confidence": 0.80},
            "language": "en",
        }

        result = PalaMapper.map_extracted_data(extracted_data)

        # Check schema metadata
        assert result["schema"] == "pala_metadata"
        assert result["version"] == "1.0.0"

        # Check document_metadata
        assert result["document_metadata"]["type"]["value"] == "letter"
        assert result["document_metadata"]["type"]["confidence"] == 0.95
        assert result["document_metadata"]["date"]["value"] == "1892-03-15"
        assert result["document_metadata"]["date"]["confidence"] == 0.88
        assert result["document_metadata"]["date"]["format"] == "ISO8601"
        assert result["document_metadata"]["language"] == "en"

        # Check parties
        assert len(result["parties"]["people"]) == 2
        assert result["parties"]["people"][0]["name"] == "John Smith"
        assert result["parties"]["people"][0]["role"] == "sender"
        assert result["parties"]["people"][0]["confidence"] == 0.92
        assert len(result["parties"]["organizations"]) == 1
        assert result["parties"]["organizations"][0]["name"] == "Monastery Board"
        assert result["parties"]["overall_confidence"] == 0.90

        # Check places
        assert len(result["places"]["locations"]) == 2
        assert result["places"]["locations"][0]["name"] == "London"
        assert result["places"]["locations"][0]["role"] == "origin"
        assert result["places"]["overall_confidence"] == 0.92

        # Check storage
        assert result["storage"]["archive"] == "Pala Sangha"
        assert result["storage"]["collection"] == "Letters"
        assert result["storage"]["box"] == "15"
        assert result["storage"]["folder"] == "3"
        assert result["storage"]["confidence"] == 0.75

        # Check access
        assert result["access"]["level"] == "public"
        assert result["access"]["reasoning"] == "Historical document, no sensitive info"
        assert result["access"]["confidence"] == 0.85

        # Check content
        assert result["content"]["summary"]["text"] == "Letter about monastery matters"
        assert result["content"]["summary"]["confidence"] == 0.88
        assert result["content"]["topics"]["topics"] == ["Buddhism", "Administration", "Correspondence"]
        assert result["content"]["topics"]["confidence"] == 0.82
        assert result["content"]["tone_sentiment"]["tone"] == "formal"
        assert result["content"]["tone_sentiment"]["sentiment"] == "neutral"
        assert result["content"]["tone_sentiment"]["confidence"] == 0.80

        # Check quality metrics
        assert "overall_confidence" in result["quality_metrics"]
        assert result["quality_metrics"]["overall_confidence"] > 0.0
        assert "field_confidences" in result["quality_metrics"]

    def test_map_extracted_data_minimal(self):
        """Test mapping with minimal/empty data"""
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

        result = PalaMapper.map_extracted_data(extracted_data)

        assert result["schema"] == "pala_metadata"
        assert result["document_metadata"]["type"]["value"] == "unknown"
        assert result["parties"]["people"] == []
        assert result["places"]["locations"] == []
        assert result["storage"]["archive"] is None
        assert result["content"]["summary"]["text"] == ""
        assert result["quality_metrics"]["overall_confidence"] == 0.0

    def test_extract_document_type(self):
        """Test document type extraction"""
        data = {"document_type": {"value": "telegram", "confidence": 0.93}}
        result = PalaMapper._extract_document_type(data)
        assert result["value"] == "telegram"
        assert result["confidence"] == 0.93

    def test_extract_document_type_missing(self):
        """Test document type extraction with missing data"""
        data = {}
        result = PalaMapper._extract_document_type(data)
        assert result["value"] == "unknown"
        assert result["confidence"] == 0.0

    def test_extract_document_date(self):
        """Test document date extraction"""
        data = {"document_date": {"value": "2024-01-15", "confidence": 0.87}}
        result = PalaMapper._extract_document_date(data)
        assert result["value"] == "2024-01-15"
        assert result["confidence"] == 0.87
        assert result["format"] == "ISO8601"

    def test_extract_parties_empty(self):
        """Test parties extraction with no parties"""
        data = {"parties": {"people": [], "organizations": [], "confidence": 0.0}}
        result = PalaMapper._extract_parties(data)
        assert result["people"] == []
        assert result["organizations"] == []
        assert result["overall_confidence"] == 0.0

    def test_extract_places_multiple(self):
        """Test places extraction with multiple locations"""
        data = {
            "places": {
                "locations": [
                    {"name": "Delhi", "role": "mentioned", "confidence": 0.88},
                    {"name": "Mumbai", "role": "mentioned", "confidence": 0.85},
                ],
                "confidence": 0.87,
            }
        }
        result = PalaMapper._extract_places(data)
        assert len(result["locations"]) == 2
        assert result["locations"][0]["name"] == "Delhi"
        assert result["overall_confidence"] == 0.87

    def test_extract_storage_location_partial(self):
        """Test storage location with partial data"""
        data = {
            "storage_location": {
                "archive": "National Archives",
                "collection": None,
                "box": "42",
                "folder": None,
                "confidence": 0.65,
            }
        }
        result = PalaMapper._extract_storage_location(data)
        assert result["archive"] == "National Archives"
        assert result["collection"] is None
        assert result["box"] == "42"
        assert result["confidence"] == 0.65

    def test_extract_access_level(self):
        """Test access level extraction"""
        data = {
            "access_level": {
                "value": "restricted",
                "reasoning": "Contains personal information",
                "confidence": 0.78,
            }
        }
        result = PalaMapper._extract_access_level(data)
        assert result["level"] == "restricted"
        assert result["reasoning"] == "Contains personal information"
        assert result["confidence"] == 0.78

    def test_calculate_overall_confidence(self):
        """Test overall confidence calculation"""
        data = {
            "document_type": {"value": "letter", "confidence": 0.95},
            "document_date": {"value": "1892-03-15", "confidence": 0.88},
            "access_level": {"value": "public", "confidence": 0.85},
            "summary": {"value": "Test", "confidence": 0.90},
        }
        result = PalaMapper._calculate_overall_confidence(data)
        assert result > 0.85
        assert result < 0.95
        assert isinstance(result, float)

    def test_calculate_overall_confidence_empty(self):
        """Test confidence calculation with no confidence scores"""
        data = {"some_field": "value"}
        result = PalaMapper._calculate_overall_confidence(data)
        assert result == 0.0

    def test_extract_field_confidences(self):
        """Test field confidence extraction"""
        data = {
            "document_type": {"value": "letter", "confidence": 0.95},
            "document_date": {"value": "1892-03-15", "confidence": 0.88},
            "summary": {"value": "Test", "confidence": 0.90},
            "parties": {"people": [], "confidence": 0.75},
        }
        result = PalaMapper._extract_field_confidences(data)
        assert result["document_type"] == 0.95
        assert result["document_date"] == 0.88
        assert result["summary"] == 0.90
        assert result["parties"] == 0.75

    def test_extract_tone_sentiment(self):
        """Test tone and sentiment extraction"""
        data = {"tone_sentiment": {"tone": "urgent", "sentiment": "negative", "confidence": 0.72}}
        result = PalaMapper._extract_tone_sentiment(data)
        assert result["tone"] == "urgent"
        assert result["sentiment"] == "negative"
        assert result["confidence"] == 0.72

    def test_extract_key_topics(self):
        """Test key topics extraction"""
        data = {"key_topics": {"topics": ["Religion", "Politics", "Trade"], "confidence": 0.81}}
        result = PalaMapper._extract_key_topics(data)
        assert result["topics"] == ["Religion", "Politics", "Trade"]
        assert result["confidence"] == 0.81
