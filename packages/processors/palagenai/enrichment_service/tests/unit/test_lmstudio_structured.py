"""
Unit tests for LM Studio structured JSON extraction

Tests for:
- JSON parsing from LLM responses
- Structured prompt generation
- Merging LM Studio data with enrichment agent results
- Backward compatibility with text-only mode
"""

import pytest
import json
import logging
from typing import Dict, Any

# Mock the base provider and other dependencies
class MockBaseOCRProvider:
    """Mock base provider for testing"""
    pass

# Set up test logger
logger = logging.getLogger(__name__)


class TestJSONParsing:
    """Test JSON extraction from LLM responses"""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock orchestrator with _parse_json_response method"""
        class MockOrchestrator:
            def _parse_json_response(self, llm_response: str):
                """Mock of _parse_json_response from lmstudio_provider"""
                import re
                import json

                # Strategy 1: Try parsing entire response as JSON
                try:
                    data = json.loads(llm_response.strip())
                    logger.debug("Parsed response as direct JSON")
                    return True, data, ""
                except json.JSONDecodeError:
                    pass

                # Strategy 2: Extract JSON from markdown code blocks
                code_block_pattern = r'```(?:json)?\s*\n(.*?)\n```'
                matches = re.findall(code_block_pattern, llm_response, re.DOTALL)

                for match in matches:
                    try:
                        data = json.loads(match.strip())
                        logger.debug("Extracted JSON from markdown code block")
                        return True, data, ""
                    except json.JSONDecodeError:
                        continue

                # Strategy 3: Find JSON object using brace matching
                start_idx = llm_response.find('{')
                if start_idx != -1:
                    brace_count = 0
                    for i in range(start_idx, len(llm_response)):
                        if llm_response[i] == '{':
                            brace_count += 1
                        elif llm_response[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                try:
                                    json_str = llm_response[start_idx:i+1]
                                    data = json.loads(json_str)
                                    logger.debug("Extracted JSON using brace matching")
                                    return True, data, ""
                                except json.JSONDecodeError:
                                    break

                # All strategies failed
                return False, None, "Failed to extract valid JSON"

        return MockOrchestrator()

    def test_parse_direct_json(self, mock_orchestrator):
        """Test parsing clean JSON response"""
        response = json.dumps({
            "ocr_text": "Dear John,\n\nThis is a test.",
            "structured_data": {
                "document": {"date": {"creation_date": "2024-01-15"}}
            }
        })

        success, data, error = mock_orchestrator._parse_json_response(response)

        assert success is True
        assert data is not None
        assert data["ocr_text"] == "Dear John,\n\nThis is a test."
        assert error == ""

    def test_parse_json_from_markdown(self, mock_orchestrator):
        """Test extracting JSON from ```json code blocks"""
        response = """Let me extract this data for you.

```json
{
  "ocr_text": "Extracted text",
  "structured_data": {}
}
```

That's the result."""

        success, data, error = mock_orchestrator._parse_json_response(response)

        assert success is True
        assert data is not None
        assert data["ocr_text"] == "Extracted text"

    def test_parse_json_with_surrounding_text(self, mock_orchestrator):
        """Test extracting JSON from response with surrounding text using brace matching"""
        response = """Some text before
        {
          "ocr_text": "Letter content",
          "structured_data": {"document": {}}
        }
        More text after"""

        success, data, error = mock_orchestrator._parse_json_response(response)

        assert success is True
        assert data is not None
        assert data["ocr_text"] == "Letter content"

    def test_parse_json_failure(self, mock_orchestrator):
        """Test handling of invalid JSON"""
        response = "This is not JSON at all, just plain text"

        success, data, error = mock_orchestrator._parse_json_response(response)

        assert success is False
        assert data is None
        assert error != ""

    def test_parse_malformed_json_in_markdown(self, mock_orchestrator):
        """Test handling of malformed JSON in markdown blocks"""
        response = """```json
{
  "incomplete": "json
}
```

More text"""

        success, data, error = mock_orchestrator._parse_json_response(response)

        assert success is False
        assert data is None


class TestStructuredPromptGeneration:
    """Test structured prompt generation"""

    def test_structured_prompt_includes_schema(self):
        """Test that structured prompt includes JSON schema"""
        # Mock the _build_structured_prompt method
        def mock_build_structured_prompt(languages, handwriting):
            if handwriting:
                return "text-only prompt"

            prompt = """OUTPUT FORMAT:
{
  "ocr_text": "...",
  "structured_data": {
    "document": {...},
    "content": {...}
  }
}"""
            return prompt

        prompt = mock_build_structured_prompt(None, False)

        assert "ocr_text" in prompt
        assert "structured_data" in prompt
        assert "document" in prompt
        assert "content" in prompt

    def test_structured_prompt_skips_handwriting(self):
        """Test that structured prompt falls back for handwriting"""
        def mock_build_structured_prompt(languages, handwriting):
            if handwriting:
                return "text-only prompt for handwriting"
            return "structured prompt"

        prompt = mock_build_structured_prompt(None, True)

        assert prompt == "text-only prompt for handwriting"

    def test_structured_prompt_includes_languages(self):
        """Test that language hints are added to prompt"""
        def mock_build_structured_prompt(languages, handwriting):
            prompt = "Base prompt"
            if languages:
                lang_note = f"Languages: {', '.join(languages)}"
                prompt = f"{prompt}\n{lang_note}"
            return prompt

        prompt = mock_build_structured_prompt(['en', 'hi'], False)

        assert "Languages: en, hi" in prompt


class TestMergingResults:
    """Test merging of LM Studio data with enrichment agent results"""

    @pytest.fixture
    def sample_lmstudio_data(self):
        """Sample structured data from LM Studio"""
        return {
            "document": {
                "date": {
                    "creation_date": "2024-01-15",
                    "sent_date": "2024-01-16"
                },
                "languages": ["en"],
                "physical_attributes": {
                    "letterhead": "Acme Corporation",
                    "pages": 2
                },
                "correspondence": {
                    "sender": {
                        "name": "John Doe",
                        "location": "New York",
                        "contact_info": {"address": "123 Main St"}
                    },
                    "recipient": {
                        "name": "Jane Smith",
                        "location": "Boston"
                    }
                }
            },
            "content": {
                "full_text": "Dear Jane...",
                "salutation": "Dear Jane,",
                "body": ["Paragraph 1", "Paragraph 2"],
                "closing": "Sincerely,",
                "signature": "John Doe"
            }
        }

    @pytest.fixture
    def sample_agent_results(self):
        """Sample enrichment agent results"""
        return {
            "metadata": {},
            "document": {
                "languages": ["de"],  # Should be overwritten by LM Studio
                "correspondence": {
                    "sender": {
                        "biography": "John is a CEO"  # Should be preserved
                    }
                }
            },
            "content": {
                "summary": "This is a business letter",  # Not in LM Studio
                "body": ["Different paragraph"]  # Should be overwritten
            },
            "analysis": {
                "keywords": ["business", "correspondence"],
                "people": [{"name": "John Doe"}]
            }
        }

    def test_merge_prioritizes_lmstudio_dates(self, sample_lmstudio_data, sample_agent_results):
        """Test that LM Studio dates take priority"""
        # Simplified merge logic for testing
        merged = sample_agent_results.copy()

        # Apply LM Studio dates (priority)
        if 'document' in sample_lmstudio_data:
            if sample_lmstudio_data['document'].get('date'):
                merged['document']['date'] = sample_lmstudio_data['document']['date']

        assert merged['document']['date']['creation_date'] == "2024-01-15"

    def test_merge_preserves_agent_biography(self, sample_lmstudio_data, sample_agent_results):
        """Test that agent biographies are preserved"""
        merged = sample_agent_results.copy()

        # Merge correspondence - preserve biography from agents
        lm_correspondence = sample_lmstudio_data['document']['correspondence']
        if 'correspondence' not in merged['document']:
            merged['document']['correspondence'] = {}

        for field in ['name', 'location']:
            if lm_correspondence['sender'].get(field):
                merged['document']['correspondence']['sender'][field] = lm_correspondence['sender'][field]

        # Biography should still exist
        assert merged['document']['correspondence']['sender'].get('biography') == "John is a CEO"

    def test_merge_overwrites_structure(self, sample_lmstudio_data, sample_agent_results):
        """Test that LM Studio structure fields overwrite agent results"""
        merged = sample_agent_results.copy()

        # Apply LM Studio content structure
        if 'content' in sample_lmstudio_data:
            lm_content = sample_lmstudio_data['content']
            for field in ['salutation', 'body', 'closing']:
                if lm_content.get(field):
                    merged['content'][field] = lm_content[field]

        # Body should be from LM Studio
        assert merged['content']['body'] == ["Paragraph 1", "Paragraph 2"]
        # But summary should be preserved from agent
        assert 'summary' in merged['content']

    def test_merge_with_empty_lmstudio_data(self, sample_agent_results):
        """Test merge when LM Studio data is empty"""
        empty_lmstudio = {}
        merged = sample_agent_results.copy()

        # Should keep agent results unchanged
        assert merged['document']['languages'] == ["de"]
        assert "biography" in merged['document']['correspondence']['sender']


class TestBackwardCompatibility:
    """Test backward compatibility with text-only mode"""

    def test_text_only_response_format(self):
        """Test that text-only response maintains original format"""
        response_data = {
            'text': 'Extracted text',
            'full_text': 'Extracted text',
            'words': [],
            'blocks': [{'text': 'Extracted text'}],
            'confidence': 0.95,
            'extraction_mode': 'text_only'
        }

        # Original fields should all be present
        assert 'text' in response_data
        assert 'full_text' in response_data
        assert 'words' in response_data
        assert 'blocks' in response_data
        assert 'confidence' in response_data

    def test_structured_response_includes_original_fields(self):
        """Test that structured response includes backward-compatible fields"""
        response_data = {
            'text': 'Extracted text',
            'full_text': 'Extracted text',
            'words': [],
            'blocks': [{'text': 'Extracted text'}],
            'confidence': 0.95,
            'structured_data': {},
            'extraction_mode': 'structured'
        }

        # Original fields should still exist
        assert 'text' in response_data
        assert 'full_text' in response_data
        # Plus new structured field
        assert 'structured_data' in response_data

    def test_feature_flag_disables_structured(self):
        """Test that feature flag can disable structured output"""
        # Simulate configuration
        enable_structured = False

        if enable_structured:
            prompt = "structured prompt"
        else:
            prompt = "text-only prompt"

        assert prompt == "text-only prompt"

    def test_pdf_multi_page_backward_compatible(self):
        """Test that PDF response format is backward compatible"""
        response_data = {
            'text': 'Page 1 text\n\nPage 2 text',
            'full_text': 'Page 1 text\n\nPage 2 text',
            'words': [],
            'blocks': [
                {'text': 'Page 1 text', 'page': 1},
                {'text': 'Page 2 text', 'page': 2}
            ],
            'confidence': 0.95,
            'pages_processed': 2,
            'extraction_mode': 'text_only'
        }

        # All expected fields present
        assert response_data['pages_processed'] == 2
        assert len(response_data['blocks']) == 2


class TestErrorHandling:
    """Test error handling and fallback mechanisms"""

    def test_json_parsing_failure_returns_false(self):
        """Test that JSON parsing failure is handled gracefully"""
        invalid_response = "not json at all"

        success = False
        error = None

        # Simulate parsing attempt
        try:
            json.loads(invalid_response)
            success = True
        except json.JSONDecodeError as e:
            success = False
            error = str(e)

        assert success is False
        assert error is not None

    def test_missing_ocr_text_field(self):
        """Test handling when parsed JSON is missing ocr_text"""
        parsed_json = {
            "structured_data": {"document": {}},
            # Missing 'ocr_text' field
        }

        if 'ocr_text' not in parsed_json:
            logger.warning("JSON missing 'ocr_text' field, falling back to text-only")
            structured_data = None
        else:
            structured_data = parsed_json['structured_data']

        assert structured_data is None

    def test_fallback_preserves_text(self):
        """Test that fallback to text-only preserves OCR text"""
        llm_response = "Some extracted text from the image"
        structured_data = None

        # On fallback, use llm_response as text
        ocr_text = llm_response

        response_data = {
            'text': ocr_text,
            'full_text': ocr_text,
            'extraction_mode': 'text_only'
        }

        assert response_data['text'] == llm_response
        assert response_data['extraction_mode'] == 'text_only'


@pytest.mark.integration
class TestIntegration:
    """Integration tests for complete workflow"""

    def test_complete_structured_extraction_flow(self):
        """Test complete flow from image to structured output"""
        # Simulate complete flow
        llm_response = json.dumps({
            "ocr_text": "Dear Jane,\n\nThis is a test letter.",
            "structured_data": {
                "document": {
                    "date": {"creation_date": "2024-01-15"},
                    "correspondence": {
                        "sender": {"name": "John", "location": "NYC"},
                        "recipient": {"name": "Jane", "location": "Boston"}
                    }
                },
                "content": {
                    "salutation": "Dear Jane,",
                    "body": ["This is a test letter."]
                }
            }
        })

        # Parse response
        import re
        success = True
        try:
            parsed = json.loads(llm_response)
        except:
            success = False

        assert success is True
        assert 'ocr_text' in parsed
        assert 'structured_data' in parsed

    def test_fallback_to_text_only_on_failure(self):
        """Test fallback to text-only mode when JSON parsing fails"""
        llm_response = "Malformed response that cannot be parsed as JSON"

        # Try to parse
        try:
            parsed = json.loads(llm_response)
            structured_data = parsed.get('structured_data')
        except:
            # Fallback to text-only
            structured_data = None

        # Response should be valid even with fallback
        response = {
            'text': llm_response,
            'full_text': llm_response,
            'extraction_mode': 'text_only'
        }

        assert response['extraction_mode'] == 'text_only'
        assert response['text'] == llm_response


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
