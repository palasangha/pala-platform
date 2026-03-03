"""
Unit tests for ClaudeMetadataProvider
"""

import pytest
import json
import sys
from unittest.mock import Mock, patch, AsyncMock, MagicMock


class TestClaudeMetadataProvider:
    """Test suite for Claude metadata provider"""

    def test_init_with_api_key(self):
        """Test provider initialization with API key"""
        # Mock the anthropic module before import
        mock_anthropic_module = MagicMock()
        mock_client = Mock()
        mock_anthropic_module.Anthropic.return_value = mock_client
        
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch.dict('sys.modules', {'anthropic': mock_anthropic_module}):
                from providers.claude_provider import ClaudeMetadataProvider
                
                provider = ClaudeMetadataProvider(api_key="test-key")
                assert provider.api_key == "test-key"
                assert provider.model == "claude-3-5-sonnet-20241022"
                assert provider.client == mock_client

    def test_init_without_api_key(self):
        """Test provider initialization without API key"""
        with patch.dict("os.environ", {}, clear=True):
            with patch.dict('sys.modules', {'anthropic': MagicMock()}):
                from providers.claude_provider import ClaudeMetadataProvider
                provider = ClaudeMetadataProvider()
                assert not provider.is_available()
                assert provider.client is None

    def test_init_disabled(self):
        """Test provider initialization when disabled"""
        with patch.dict("os.environ", {"CLAUDE_ENABLED": "false"}):
            with patch.dict('sys.modules', {'anthropic': MagicMock()}):
                from providers.claude_provider import ClaudeMetadataProvider
                provider = ClaudeMetadataProvider()
                assert not provider.is_available()

    def test_init_missing_anthropic_package(self):
        """Test initialization fails gracefully when anthropic package missing"""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch.dict('sys.modules', {'anthropic': None}):
                # Force reimport to trigger ImportError handling
                import importlib
                if 'providers.claude_provider' in sys.modules:
                    del sys.modules['providers.claude_provider']
                from providers.claude_provider import ClaudeMetadataProvider
                
                provider = ClaudeMetadataProvider()
                assert provider.is_available() is False

    @pytest.mark.asyncio
    async def test_extract_metadata_empty_text(self):
        """Test extraction fails with empty OCR text"""
        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = Mock()
        
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch.dict('sys.modules', {'anthropic': mock_anthropic_module}):
                from providers.claude_provider import ClaudeMetadataProvider
                
                provider = ClaudeMetadataProvider()
                with pytest.raises(ValueError, match="OCR text cannot be empty"):
                    await provider.extract_metadata("")

    @pytest.mark.asyncio
    async def test_extract_metadata_provider_unavailable(self):
        """Test extraction fails when provider unavailable"""
        with patch.dict('sys.modules', {'anthropic': MagicMock()}):
            from providers.claude_provider import ClaudeMetadataProvider
            provider = ClaudeMetadataProvider()
            provider._available = False

            with pytest.raises(ValueError, match="Claude provider is not available"):
                await provider.extract_metadata("some text")

    @pytest.mark.asyncio
    async def test_extract_metadata_success(self):
        """Test successful metadata extraction"""
        mock_response = {
            "document_type": {"value": "letter", "confidence": 0.95},
            "document_date": {"value": "1892-03-15", "confidence": 0.88},
            "parties": {
                "people": [{"name": "John Smith", "role": "sender", "confidence": 0.92}],
                "organizations": [],
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
            "summary": {"value": "Letter about monastery matters", "confidence": 0.88},
            "key_topics": {
                "topics": ["Buddhism", "Administration"],
                "confidence": 0.82,
            },
            "tone_sentiment": {"tone": "formal", "sentiment": "neutral", "confidence": 0.80},
            "language": "en",
            "notes": None,
        }

        mock_anthropic_module = MagicMock()
        mock_client = Mock()
        mock_anthropic_module.Anthropic.return_value = mock_client
        
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch.dict('sys.modules', {'anthropic': mock_anthropic_module}):
                from providers.claude_provider import ClaudeMetadataProvider
                
                provider = ClaudeMetadataProvider()

                # Mock Claude API response
                mock_message = Mock()
                mock_message.content = [Mock(text=json.dumps(mock_response))]
                provider.client.messages = Mock()
                provider.client.messages.create = Mock(return_value=mock_message)

                result = await provider.extract_metadata("Dear Sir, this is a letter...")

                assert result["document_type"]["value"] == "letter"
                assert result["document_type"]["confidence"] == 0.95
                assert result["parties"]["people"][0]["name"] == "John Smith"
                assert result["language"] == "en"

                # Verify Claude API was called correctly
                provider.client.messages.create.assert_called_once()
                call_args = provider.client.messages.create.call_args
                assert call_args[1]["model"] == "claude-3-5-sonnet-20241022"
                assert call_args[1]["temperature"] == 0.2

    @pytest.mark.asyncio
    async def test_extract_metadata_invalid_json(self):
        """Test extraction fails with invalid JSON response"""
        mock_anthropic_module = MagicMock()
        mock_client = Mock()
        mock_anthropic_module.Anthropic.return_value = mock_client
        
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch.dict('sys.modules', {'anthropic': mock_anthropic_module}):
                from providers.claude_provider import ClaudeMetadataProvider
                
                provider = ClaudeMetadataProvider()

                # Mock invalid JSON response
                mock_message = Mock()
                mock_message.content = [Mock(text="This is not valid JSON")]
                provider.client.messages = Mock()
                provider.client.messages.create = Mock(return_value=mock_message)

                with pytest.raises(ValueError, match="Could not parse Claude response"):
                    await provider.extract_metadata("Dear Sir...")

    @pytest.mark.asyncio
    async def test_extract_metadata_with_custom_prompt(self):
        """Test extraction with custom prompt"""
        mock_response = {
            "document_type": {"value": "memo", "confidence": 0.90},
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
            "access_level": {"value": "public", "reasoning": "", "confidence": 0.5},
            "summary": {"value": "Brief memo", "confidence": 0.7},
            "key_topics": {"topics": [], "confidence": 0.0},
            "tone_sentiment": {"tone": "informal", "sentiment": "neutral", "confidence": 0.6},
            "language": "en",
            "notes": None,
        }

        mock_anthropic_module = MagicMock()
        mock_client = Mock()
        mock_anthropic_module.Anthropic.return_value = mock_client
        
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch.dict('sys.modules', {'anthropic': mock_anthropic_module}):
                from providers.claude_provider import ClaudeMetadataProvider
                
                provider = ClaudeMetadataProvider()

                mock_message = Mock()
                mock_message.content = [Mock(text=json.dumps(mock_response))]
                provider.client.messages = Mock()
                provider.client.messages.create = Mock(return_value=mock_message)

                custom_prompt = "Extract only the document type and summary"
                result = await provider.extract_metadata(
                    ocr_text="Quick memo...", custom_prompt=custom_prompt
                )

                # Verify custom prompt was used
                call_args = provider.client.messages.create.call_args
                assert custom_prompt in call_args[1]["messages"][0]["content"]

    def test_parse_claude_response_valid_json(self):
        """Test parsing valid JSON response"""
        with patch.dict('sys.modules', {'anthropic': MagicMock()}):
            from providers.claude_provider import ClaudeMetadataProvider
            provider = ClaudeMetadataProvider()
            response = '{"document_type": {"value": "letter", "confidence": 0.95}}'
            result = provider._parse_claude_response(response)
            assert result["document_type"]["value"] == "letter"

    def test_parse_claude_response_json_in_text(self):
        """Test parsing JSON embedded in text"""
        with patch.dict('sys.modules', {'anthropic': MagicMock()}):
            from providers.claude_provider import ClaudeMetadataProvider
            provider = ClaudeMetadataProvider()
            response = 'Here is the result: {"document_type": {"value": "memo", "confidence": 0.90}} end'
            result = provider._parse_claude_response(response)
            assert result["document_type"]["value"] == "memo"

    def test_parse_claude_response_invalid(self):
        """Test parsing fails with invalid response"""
        with patch.dict('sys.modules', {'anthropic': MagicMock()}):
            from providers.claude_provider import ClaudeMetadataProvider
            provider = ClaudeMetadataProvider()
            with pytest.raises(ValueError, match="Could not parse Claude response"):
                provider._parse_claude_response("Not JSON at all")

    def test_build_extraction_prompt_basic(self):
        """Test building basic extraction prompt"""
        with patch.dict('sys.modules', {'anthropic': MagicMock()}):
            from providers.claude_provider import ClaudeMetadataProvider
            provider = ClaudeMetadataProvider()
            prompt = provider._build_extraction_prompt()
            assert "expert historical document analyst" in prompt
            assert "confidence" in prompt
            assert "document_type" in prompt
            assert "CRITICAL REQUIREMENTS" in prompt

    def test_build_extraction_prompt_with_language(self):
        """Test building prompt with language hint"""
        with patch.dict('sys.modules', {'anthropic': MagicMock()}):
            from providers.claude_provider import ClaudeMetadataProvider
            provider = ClaudeMetadataProvider()
            prompt = provider._build_extraction_prompt(language="hi")
            assert "hi" in prompt
            assert "language hint" in prompt

    def test_build_extraction_prompt_with_context(self):
        """Test building prompt with document context"""
        with patch.dict('sys.modules', {'anthropic': MagicMock()}):
            from providers.claude_provider import ClaudeMetadataProvider
            provider = ClaudeMetadataProvider()
            prompt = provider._build_extraction_prompt(document_context="monastery_record")
            assert "monastery_record" in prompt
        assert "context" in prompt
