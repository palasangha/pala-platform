"""
Unit tests for MetadataExtractionAgent
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from main import MetadataExtractionAgent


class TestMetadataExtractionAgent:
    """Test suite for metadata extraction agent"""

    def test_init(self):
        """Test agent initialization"""
        with patch.dict("os.environ", {"MCP_AGENT_ID": "test-agent", "MCP_SERVER_URL": "ws://test:3000"}):
            with patch("main.ClaudeMetadataProvider"):
                agent = MetadataExtractionAgent()
                assert agent.agent_id == "test-agent"
                assert agent.server_url == "ws://test:3000"

    def test_get_provider_claude(self):
        """Test getting Claude provider"""
        with patch("main.ClaudeMetadataProvider") as mock_claude:
            agent = MetadataExtractionAgent()
            provider = agent.get_provider("claude")
            assert provider == agent.claude_provider

    def test_get_provider_unsupported(self):
        """Test getting unsupported provider"""
        with patch("main.ClaudeMetadataProvider"):
            agent = MetadataExtractionAgent()
            with pytest.raises(ValueError, match="Unsupported model"):
                agent.get_provider("unsupported_model")

    @pytest.mark.asyncio
    async def test_extract_metadata_missing_ocr_text(self):
        """Test extraction fails without ocr_text"""
        with patch("main.ClaudeMetadataProvider"):
            agent = MetadataExtractionAgent()
            with pytest.raises(ValueError, match="ocr_text is required"):
                await agent.extract_metadata({"model": "claude", "output_type": "pala"})

    @pytest.mark.asyncio
    async def test_extract_metadata_invalid_output_type(self):
        """Test extraction fails with invalid output_type"""
        with patch("main.ClaudeMetadataProvider"):
            agent = MetadataExtractionAgent()
            with pytest.raises(ValueError, match="output_type must be"):
                await agent.extract_metadata({
                    "ocr_text": "test",
                    "model": "claude",
                    "output_type": "invalid"
                })

    @pytest.mark.asyncio
    async def test_extract_metadata_provider_unavailable(self):
        """Test extraction fails when provider unavailable"""
        with patch("main.ClaudeMetadataProvider") as mock_claude:
            mock_provider = Mock()
            mock_provider.is_available.return_value = False
            mock_claude.return_value = mock_provider

            agent = MetadataExtractionAgent()
            agent.claude_provider = mock_provider

            with pytest.raises(ValueError, match="Provider .* is not available"):
                await agent.extract_metadata({
                    "ocr_text": "test",
                    "model": "claude",
                    "output_type": "pala"
                })

    @pytest.mark.asyncio
    async def test_extract_metadata_pala_output(self):
        """Test extraction with Pala output type"""
        mock_extracted_data = {
            "document_type": {"value": "letter", "confidence": 0.95},
            "document_date": {"value": "1892-03-15", "confidence": 0.88},
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
            "summary": {"value": "Test", "confidence": 0.8},
            "key_topics": {"topics": [], "confidence": 0.0},
            "tone_sentiment": {"tone": "formal", "sentiment": "neutral", "confidence": 0.7},
            "language": "en",
        }

        with patch("main.ClaudeMetadataProvider") as mock_claude:
            mock_provider = AsyncMock()
            mock_provider.is_available.return_value = True
            mock_provider.extract_metadata.return_value = mock_extracted_data
            mock_claude.return_value = mock_provider

            agent = MetadataExtractionAgent()
            agent.claude_provider = mock_provider

            result = await agent.extract_metadata({
                "ocr_text": "Dear Sir...",
                "model": "claude",
                "output_type": "pala"
            })

            assert result["schema_version"] == "1.0.0"
            assert "extraction_metadata" in result
            assert "confidence_scores" in result
            assert "pala_metadata" in result
            assert "archipelago_metadata" not in result
            assert result["pala_metadata"]["schema"] == "pala_metadata"

    @pytest.mark.asyncio
    async def test_extract_metadata_archipelago_output(self):
        """Test extraction with Archipelago output type"""
        mock_extracted_data = {
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
            "access_level": {"value": "restricted", "reasoning": "Sensitive", "confidence": 0.75},
            "summary": {"value": "Internal memo", "confidence": 0.85},
            "key_topics": {"topics": ["Administration"], "confidence": 0.8},
            "tone_sentiment": {"tone": "informal", "sentiment": "neutral", "confidence": 0.7},
            "language": "en",
        }

        with patch("main.ClaudeMetadataProvider") as mock_claude:
            mock_provider = AsyncMock()
            mock_provider.is_available.return_value = True
            mock_provider.extract_metadata.return_value = mock_extracted_data
            mock_claude.return_value = mock_provider

            agent = MetadataExtractionAgent()
            agent.claude_provider = mock_provider

            result = await agent.extract_metadata({
                "ocr_text": "Memo...",
                "model": "claude",
                "output_type": "archipelago"
            })

            assert "archipelago_metadata" in result
            assert "pala_metadata" not in result
            assert result["archipelago_metadata"]["schema"] == "archipelago_commons"

    @pytest.mark.asyncio
    async def test_extract_metadata_combined_output(self):
        """Test extraction with combined output type"""
        mock_extracted_data = {
            "document_type": {"value": "letter", "confidence": 0.95},
            "document_date": {"value": "1892-03-15", "confidence": 0.88},
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
            "summary": {"value": "Test", "confidence": 0.8},
            "key_topics": {"topics": [], "confidence": 0.0},
            "tone_sentiment": {"tone": "formal", "sentiment": "neutral", "confidence": 0.7},
            "language": "en",
        }

        with patch("main.ClaudeMetadataProvider") as mock_claude:
            mock_provider = AsyncMock()
            mock_provider.is_available.return_value = True
            mock_provider.extract_metadata.return_value = mock_extracted_data
            mock_claude.return_value = mock_provider

            agent = MetadataExtractionAgent()
            agent.claude_provider = mock_provider

            result = await agent.extract_metadata({
                "ocr_text": "Dear Sir...",
                "model": "claude",
                "output_type": "combined"
            })

            assert "pala_metadata" in result
            assert "archipelago_metadata" in result
            assert "extracted_fields" in result
            assert result["extracted_fields"]["document_type"]["value"] == "letter"

    @pytest.mark.asyncio
    async def test_extract_metadata_with_optional_params(self):
        """Test extraction with optional parameters"""
        mock_extracted_data = {
            "document_type": {"value": "letter", "confidence": 0.95},
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
            "summary": {"value": "Test", "confidence": 0.8},
            "key_topics": {"topics": [], "confidence": 0.0},
            "tone_sentiment": {"tone": "formal", "sentiment": "neutral", "confidence": 0.7},
            "language": "hi",
        }

        with patch("main.ClaudeMetadataProvider") as mock_claude:
            mock_provider = AsyncMock()
            mock_provider.is_available.return_value = True
            mock_provider.extract_metadata.return_value = mock_extracted_data
            mock_claude.return_value = mock_provider

            agent = MetadataExtractionAgent()
            agent.claude_provider = mock_provider

            result = await agent.extract_metadata({
                "ocr_text": "पत्र...",
                "model": "claude",
                "output_type": "pala",
                "language": "hi",
                "document_context": "historical_letter",
                "custom_prompt": "Custom instructions",
                "schema_version": "1.0.0"
            })

            # Verify provider was called with correct params
            mock_provider.extract_metadata.assert_called_once()
            call_kwargs = mock_provider.extract_metadata.call_args[1]
            assert call_kwargs["language"] == "hi"
            assert call_kwargs["document_context"] == "historical_letter"
            assert call_kwargs["custom_prompt"] == "Custom instructions"

            assert result["schema_version"] == "1.0.0"

    def test_extract_confidence_scores(self):
        """Test confidence score extraction"""
        extracted_data = {
            "document_type": {"value": "letter", "confidence": 0.95},
            "document_date": {"value": "1892-03-15", "confidence": 0.88},
            "summary": {"value": "Test", "confidence": 0.90},
        }
        result = MetadataExtractionAgent._extract_confidence_scores(extracted_data)
        assert result["document_type"] == 0.95
        assert result["document_date"] == 0.88
        assert result["summary"] == 0.90
        assert "overall" in result
        assert 0.88 <= result["overall"] <= 0.95

    def test_extract_confidence_scores_empty(self):
        """Test confidence score extraction with no scores"""
        extracted_data = {"some_field": "value"}
        result = MetadataExtractionAgent._extract_confidence_scores(extracted_data)
        assert result["overall"] == 0.0

    def test_get_tool_definitions(self):
        """Test tool definitions for MCP registration"""
        with patch("main.ClaudeMetadataProvider"):
            agent = MetadataExtractionAgent()
            tools = agent.get_tool_definitions()

            assert len(tools) == 1
            tool = tools[0]
            assert tool["name"] == "extract_metadata"
            assert tool["agentId"] == agent.agent_id
            assert "inputSchema" in tool
            assert "properties" in tool["inputSchema"]

            # Check required fields
            required = tool["inputSchema"]["required"]
            assert "ocr_text" in required
            assert "model" in required
            assert "output_type" in required

            # Check properties
            props = tool["inputSchema"]["properties"]
            assert "ocr_text" in props
            assert "model" in props
            assert "output_type" in props
            assert "language" in props
            assert "document_context" in props

            # Check enums
            assert "enum" in props["model"]
            assert "claude" in props["model"]["enum"]
            assert "enum" in props["output_type"]
            assert "pala" in props["output_type"]["enum"]
            assert "archipelago" in props["output_type"]["enum"]
            assert "combined" in props["output_type"]["enum"]

    @pytest.mark.asyncio
    async def test_handle_tool_invocation(self):
        """Test tool invocation handling"""
        mock_extracted_data = {
            "document_type": {"value": "letter", "confidence": 0.95},
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
            "summary": {"value": "Test", "confidence": 0.8},
            "key_topics": {"topics": [], "confidence": 0.0},
            "tone_sentiment": {"tone": "formal", "sentiment": "neutral", "confidence": 0.7},
            "language": "en",
        }

        with patch("main.ClaudeMetadataProvider") as mock_claude:
            mock_provider = AsyncMock()
            mock_provider.is_available.return_value = True
            mock_provider.extract_metadata.return_value = mock_extracted_data
            mock_claude.return_value = mock_provider

            agent = MetadataExtractionAgent()
            agent.claude_provider = mock_provider

            result = await agent.handle_tool_invocation(
                "tools/invoke",
                {
                    "name": "extract_metadata",
                    "arguments": {
                        "ocr_text": "Test",
                        "model": "claude",
                        "output_type": "pala"
                    }
                }
            )

            assert "pala_metadata" in result

    @pytest.mark.asyncio
    async def test_handle_tool_invocation_unknown_tool(self):
        """Test handling unknown tool invocation"""
        with patch("main.ClaudeMetadataProvider"):
            agent = MetadataExtractionAgent()
            with pytest.raises(ValueError, match="Unknown tool"):
                await agent.handle_tool_invocation(
                    "tools/invoke",
                    {"name": "unknown_tool", "arguments": {}}
                )
