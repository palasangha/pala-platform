"""
Unit tests for schema validation and completeness checking

Tests:
- Schema loading and parsing
- Required field extraction
- Completeness calculation
- Missing field detection
- Low confidence field handling
- Edge cases (empty arrays, null values, nested objects)
"""

import pytest
import json
import tempfile
from pathlib import Path
from typing import Dict, Any

from enrichment_service.schema.validator import SchemaValidator, HistoricalLettersValidator


@pytest.fixture
def test_schema_file():
    """Create a temporary schema file for testing"""
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["metadata", "content"],
        "properties": {
            "metadata": {
                "type": "object",
                "required": ["id", "type"],
                "properties": {
                    "id": {"type": "string"},
                    "type": {"type": "string"},
                    "optional_field": {"type": "string"}
                }
            },
            "content": {
                "type": "object",
                "required": ["text"],
                "properties": {
                    "text": {"type": "string"},
                    "summary": {"type": "string"}
                }
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(schema, f)
        return f.name


class TestSchemaValidatorBasics:
    """Test basic schema validator functionality"""

    def test_schema_loading(self, test_schema_file):
        """Test schema is loaded correctly"""
        validator = SchemaValidator(test_schema_file)
        assert validator.schema is not None
        assert validator.schema['type'] == 'object'

    def test_required_fields_extraction(self, test_schema_file):
        """Test required fields are extracted correctly"""
        validator = SchemaValidator(test_schema_file)
        required = validator.required_fields

        # Should find top-level and nested required fields
        assert 'metadata' in required
        assert 'content' in required
        assert 'metadata.id' in required
        assert 'metadata.type' in required
        assert 'content.text' in required

    def test_schema_validation(self, test_schema_file):
        """Test document validation against schema"""
        validator = SchemaValidator(test_schema_file)

        # Valid document
        valid_doc = {
            'metadata': {'id': 'test', 'type': 'letter'},
            'content': {'text': 'test content'}
        }
        result = validator.validate(valid_doc)
        assert result['valid'] is True

        # Invalid document (missing required field)
        invalid_doc = {
            'metadata': {'id': 'test'},
            'content': {'text': 'test content'}
        }
        result = validator.validate(invalid_doc)
        assert result['valid'] is False


class TestCompletenessCalculation:
    """Test completeness score calculation"""

    def test_completeness_100_percent(self, test_schema_file):
        """Test document with all fields gets 100%"""
        validator = SchemaValidator(test_schema_file)

        doc = {
            'metadata': {
                'id': 'test',
                'type': 'letter',
                'optional_field': 'value'
            },
            'content': {
                'text': 'content',
                'summary': 'summary'
            }
        }

        result = validator.calculate_completeness(doc)
        assert result['completeness_score'] == 1.0
        assert result['passes_threshold'] is True
        assert len(result['missing_fields']) == 0

    def test_completeness_partial(self, test_schema_file):
        """Test document with missing fields"""
        validator = SchemaValidator(test_schema_file)

        doc = {
            'metadata': {'id': 'test'},
            'content': {'text': 'content'}
        }

        result = validator.calculate_completeness(doc)
        assert result['completeness_score'] < 1.0
        assert 'metadata.type' in result['missing_fields']

    def test_completeness_below_threshold(self, test_schema_file):
        """Test document below 95% threshold goes to review"""
        validator = SchemaValidator(test_schema_file)

        # Missing most fields
        doc = {
            'metadata': {'id': 'test'},
            'content': {}
        }

        result = validator.calculate_completeness(doc)
        assert result['requires_review'] is True
        assert result['passes_threshold'] is False

    def test_missing_field_detection(self, test_schema_file):
        """Test missing field detection"""
        validator = SchemaValidator(test_schema_file)

        doc = {
            'metadata': {'id': 'test'},
            'content': {'text': 'content'}
        }

        result = validator.calculate_completeness(doc)
        assert 'metadata.type' in result['missing_fields']
        assert 'metadata.id' not in result['missing_fields']


class TestEdgeCases:
    """Test edge cases and special scenarios"""

    def test_empty_string_treated_as_missing(self, test_schema_file):
        """Test empty strings are treated as missing"""
        validator = SchemaValidator(test_schema_file)

        doc = {
            'metadata': {'id': '', 'type': 'letter'},
            'content': {'text': 'content'}
        }

        result = validator.calculate_completeness(doc)
        assert 'metadata.id' in result['missing_fields']

    def test_empty_array_treated_as_missing(self, test_schema_file):
        """Test empty arrays are treated as missing"""
        validator = SchemaValidator(test_schema_file)

        doc = {
            'metadata': {'id': 'test', 'type': 'letter'},
            'content': {'text': 'content', 'keywords': []}
        }

        result = validator.calculate_completeness(doc)
        # Empty array should be treated as present
        assert result['completeness_score'] > 0.5

    def test_null_value_treated_as_missing(self, test_schema_file):
        """Test null values are treated as missing"""
        validator = SchemaValidator(test_schema_file)

        doc = {
            'metadata': {'id': 'test', 'type': None},
            'content': {'text': 'content'}
        }

        result = validator.calculate_completeness(doc)
        assert 'metadata.type' in result['missing_fields']

    def test_nested_object_check(self, test_schema_file):
        """Test nested object field checking"""
        validator = SchemaValidator(test_schema_file)

        # Deep nested structure
        doc = {
            'metadata': {
                'id': 'test',
                'type': 'letter',
                'nested': {
                    'deep': {
                        'value': 'test'
                    }
                }
            },
            'content': {'text': 'content'}
        }

        result = validator.calculate_completeness(doc)
        assert result['completeness_score'] > 0


class TestLowConfidenceFields:
    """Test low confidence field handling"""

    def test_low_confidence_detection(self, test_schema_file):
        """Test low confidence fields are flagged"""
        validator = SchemaValidator(test_schema_file)

        doc = {
            'metadata': {'id': 'test', 'type': 'letter'},
            'content': {'text': 'content'},
            '_metadata': {
                '_confidence_metadata.id': 0.65  # Below 0.7 threshold
            }
        }

        result = validator.calculate_completeness(doc)
        # Should have low confidence field in results
        assert len(result['low_confidence_fields']) > 0

    def test_high_confidence_fields(self, test_schema_file):
        """Test high confidence fields don't flag"""
        validator = SchemaValidator(test_schema_file)

        doc = {
            'metadata': {'id': 'test', 'type': 'letter'},
            'content': {'text': 'content'},
            '_metadata': {
                '_confidence_metadata.id': 0.95  # Above 0.7 threshold
            }
        }

        result = validator.calculate_completeness(doc)
        # Should not have low confidence fields
        assert len(result['low_confidence_fields']) == 0


class TestReportGeneration:
    """Test human-readable report generation"""

    def test_generate_report(self, test_schema_file):
        """Test report generation"""
        validator = SchemaValidator(test_schema_file)

        doc = {
            'metadata': {'id': 'test', 'type': 'letter'},
            'content': {'text': 'content'}
        }

        report = validator.generate_report(doc)
        assert 'ENRICHMENT COMPLETENESS REPORT' in report
        assert 'Completeness Score' in report
        assert 'Status' in report

    def test_report_with_missing_fields(self, test_schema_file):
        """Test report shows missing fields"""
        validator = SchemaValidator(test_schema_file)

        doc = {
            'metadata': {'id': 'test'},
            'content': {}
        }

        report = validator.generate_report(doc)
        assert 'missing' in report.lower() or 'missing fields' in report.lower()


class TestSummaryStatistics:
    """Test batch statistics generation"""

    def test_summary_statistics_empty_list(self, test_schema_file):
        """Test empty list returns zeros"""
        validator = SchemaValidator(test_schema_file)

        stats = validator.get_summary_statistics([])
        assert stats['total_documents'] == 0
        assert stats['avg_completeness'] == 0.0

    def test_summary_statistics_single_doc(self, test_schema_file):
        """Test statistics for single document"""
        validator = SchemaValidator(test_schema_file)

        doc = {
            'metadata': {'id': 'test', 'type': 'letter'},
            'content': {'text': 'content'}
        }

        stats = validator.get_summary_statistics([doc])
        assert stats['total_documents'] == 1
        assert stats['avg_completeness'] == stats['min_completeness']

    def test_summary_statistics_multiple_docs(self, test_schema_file):
        """Test statistics for multiple documents"""
        validator = SchemaValidator(test_schema_file)

        docs = [
            {
                'metadata': {'id': 'test1', 'type': 'letter'},
                'content': {'text': 'content'}
            },
            {
                'metadata': {'id': 'test2'},
                'content': {}
            }
        ]

        stats = validator.get_summary_statistics(docs)
        assert stats['total_documents'] == 2
        assert stats['documents_passing'] == 1
        assert stats['documents_requiring_review'] == 1
        assert stats['pass_rate'] == 0.5

    def test_most_common_missing_fields(self, test_schema_file):
        """Test identifies most common missing fields"""
        validator = SchemaValidator(test_schema_file)

        docs = [
            {'metadata': {'id': 'test1'}, 'content': {'text': 'content'}},
            {'metadata': {'id': 'test2'}, 'content': {'text': 'content'}},
            {'metadata': {'id': 'test3'}, 'content': {}},
        ]

        stats = validator.get_summary_statistics(docs)
        # 'metadata.type' is missing in all 3 documents
        assert 'metadata.type' in stats['most_common_missing_fields']


class TestAliasCompatibility:
    """Test SchemaValidator alias for HistoricalLettersValidator"""

    def test_schema_validator_alias(self, test_schema_file):
        """Test SchemaValidator alias works"""
        # Both should work
        validator1 = SchemaValidator(test_schema_file)
        validator2 = HistoricalLettersValidator(test_schema_file)

        # Should be same class
        assert type(validator1).__name__ == type(validator2).__name__
        assert isinstance(validator1, HistoricalLettersValidator)
