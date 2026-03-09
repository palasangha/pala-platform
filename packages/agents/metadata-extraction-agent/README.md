# Metadata Extraction Agent

Stateless AI-powered agent for extracting structured metadata from OCR text. Part of the Pala Platform enrichment pipeline.

## Features

- **Claude AI Integration**: Uses Anthropic's Claude for high-accuracy metadata extraction
- **Ollama Integration**: Local LLM support for offline metadata extraction (no API key required)
- **Multiple Output Schemas**: Supports Pala metadata format v1.0.0 and Archipelago Commons
- **Confidence Scoring**: All extracted fields include 0.0-1.0 confidence scores
- **Schema Versioning**: Pin to specific schema versions for consistency
- **Extensible Architecture**: Easy to add support for other providers
- **MCP Integration**: Exposes metadata extraction as an MCP tool

## Setup

### 1. Install Dependencies

```bash
cd packages/agents/metadata-extraction-agent
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in this directory:

```bash
# Claude Provider (Optional)
ANTHROPIC_API_KEY=your-anthropic-api-key-here
CLAUDE_MODEL=claude-3-5-sonnet-20241022
CLAUDE_ENABLED=true

# Ollama Provider (Optional - for local LLM)
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# MCP Server Connection
MCP_SERVER_URL=ws://mcp-server:3010
MCP_AGENT_ID=metadata-extraction-agent
MCP_AGENT_TOKEN=optional-auth-token

# Logging
LOG_LEVEL=INFO
```

**Provider Setup:**
- **Claude**: Get API key at https://console.anthropic.com/
- **Ollama**: Install from https://ollama.ai and run `ollama serve`

See [OLLAMA_SETUP.md](./OLLAMA_SETUP.md) for detailed Ollama configuration.

### 3. Run the Agent

```bash
python main.py
```

## Usage

The agent exposes a single MCP tool: `extract_metadata`

### JSON-RPC Request Example

```json
{
  "jsonrpc": "2.0",
  "method": "tools/invoke",
  "params": {
    "toolName": "extract_metadata",
    "agentId": "metadata-extraction-agent",
    "arguments": {
      "ocr_text": "Dear Sir,\n\nI write to you from the archives of the Pala Sangha monastery, dated 15th March 1892...",
      "model": "claude",
      "output_type": "combined",
      "language": "en",
      "document_context": "historical_letter"
    }
  },
  "id": "request-123"
}
```

### Parameters

**Required:**
- `ocr_text` (string): OCR-extracted text from document
- `model` (string): AI provider - "claude" (others coming)
- `output_type` (string): Output schema - "pala", "archipelago", or "combined"

**Optional:**
- `language` (string): ISO language code (e.g., "en", "hi")
- `document_context` (string): Context hint (e.g., "historical_letter", "monastery_record")
- `custom_prompt` (string): Override default extraction prompt
- `schema_version` (string): Pin to specific schema version (default: "1.0.0")

### Response Example

```json
{
  "jsonrpc": "2.0",
  "result": {
    "schema_version": "1.0.0",
    "extraction_metadata": {
      "model_used": "claude",
      "timestamp": "2026-02-23T10:30:00.123456Z",
      "processing_time_ms": 2340,
      "input_length": 5420
    },
    "confidence_scores": {
      "overall": 0.92,
      "document_type": 0.95,
      "document_date": 0.88,
      "parties": 0.90,
      "places": 0.95,
      "storage_location": 0.75,
      "access_level": 0.85,
      "summary": 0.88,
      "key_topics": 0.82,
      "tone_sentiment": 0.80
    },
    "pala_metadata": {
      "schema": "pala_metadata",
      "version": "1.0.0",
      "document_metadata": {
        "type": {
          "value": "letter",
          "confidence": 0.95
        },
        "date": {
          "value": "1892-03-15",
          "confidence": 0.88,
          "format": "ISO8601"
        },
        "language": "en"
      },
      "parties": {
        "people": [
          {
            "name": "John Smith",
            "role": "sender",
            "confidence": 0.92
          }
        ],
        "organizations": [],
        "overall_confidence": 0.90
      },
      "places": {
        "locations": [
          {
            "name": "London",
            "role": "origin",
            "confidence": 0.95
          }
        ],
        "overall_confidence": 0.95
      },
      "storage": {
        "archive": "Pala Sangha",
        "collection": "Historical Letters",
        "box": "15",
        "folder": "3",
        "confidence": 0.75
      },
      "access": {
        "level": "public",
        "reasoning": "Historical document, no sensitive personal information",
        "confidence": 0.85
      },
      "content": {
        "summary": {
          "text": "Letter discussing monastery administrative matters",
          "confidence": 0.88
        },
        "topics": {
          "topics": ["Buddhism", "Monastery Administration", "Correspondence"],
          "confidence": 0.82
        },
        "tone_sentiment": {
          "tone": "formal",
          "sentiment": "neutral",
          "confidence": 0.80
        }
      },
      "quality_metrics": {
        "overall_confidence": 0.869,
        "field_confidences": {
          "document_type": 0.95,
          "document_date": 0.88,
          "parties": 0.90,
          "places": 0.95,
          "storage_location": 0.75,
          "access_level": 0.85,
          "summary": 0.88,
          "key_topics": 0.82,
          "tone_sentiment": 0.80
        }
      }
    },
    "archipelago_metadata": {
      "schema": "archipelago_commons",
      "version": "1.0.0",
      "title": "Letter discussing monastery administrative matters",
      "description": "Letter discussing monastery administrative matters",
      "subject": [
        "letter",
        "Buddhism",
        "Monastery Administration",
        "Correspondence"
      ],
      "creator": ["John Smith"],
      "contributor": [],
      "date_issued": "1892-03-15",
      "date_created": "1892-03-15",
      "spatial_coverage": ["London"],
      "type": "letter",
      "format": "text/plain",
      "language": "en",
      "identifier": null,
      "rights": "Public Domain / Open Access",
      "access_rights": "http://purl.org/coar/access_right/c_abf2",
      "is_part_of": {
        "archive": "Pala Sangha",
        "collection": "Historical Letters",
        "box": "15",
        "folder": "3"
      },
      "extent": {
        "text_length_chars": 5420
      },
      "source": "metadata_extraction_agent",
      "provenance": {
        "extraction_method": "metadata_extraction_agent",
        "extraction_timestamp": "2026-02-23T10:30:00.123456Z",
        "provider_model": "claude",
        "document_context": "historical_letter"
      },
      "confidence_metadata": {
        "overall_confidence": 0.869,
        "field_confidences": {
          "document_type": 0.95,
          "document_date": 0.88,
          "parties": 0.90,
          "places": 0.95,
          "storage_location": 0.75,
          "access_level": 0.85,
          "summary": 0.88,
          "key_topics": 0.82,
          "tone_sentiment": 0.80
        },
        "confidence_threshold": 0.75,
        "high_confidence_fields": [
          "document_type",
          "places",
          "document_date",
          "parties",
          "access_level",
          "summary"
        ],
        "low_confidence_fields": ["storage_location"]
      }
    }
  },
  "id": "request-123"
}
```

## Architecture

```
OCR Text
   │
   ▼
┌─────────────────────────────────────────┐
│   MetadataExtractionAgent               │
│  (Main orchestrator)                    │
└────────────┬────────────────────────────┘
             │
    ┌────────┴────────┐
    ▼                 ▼
┌──────────┐      ┌───────────────────┐
│ Claude   │      │ Mappers           │
│ Provider │      ├──────────────────┤
│          │      │ PalaMapper        │
│ - API    │      │ - Maps to Pala    │
│ - Parse  │      │   schema v1.0.0   │
│ - Scores │      │                   │
└──────────┘      │ ArchipelagoMapper │
                  │ - Maps to Archive │
                  │   Commons schema  │
                  └───────────────────┘
```

## Output Schemas

### Pala Metadata Schema v1.0.0

Follows the Historical Letters Collection schema defined in the design specification.

**Main fields:**
- `document_metadata`: Type, date, language
- `parties`: People and organizations
- `places`: Locations mentioned
- `storage`: Archive location info
- `access`: Access level and reasoning
- `content`: Summary, topics, tone, sentiment
- `quality_metrics`: Confidence scores

### Archipelago Commons Schema

Standardized schema used by museums and archives for digital objects.

**Main fields:**
- `title`, `description`: Document summary
- `subject`: Topics and keywords
- `creator`, `contributor`: People involved
- `date_issued`, `date_created`: Temporal metadata
- `spatial_coverage`: Places
- `type`: Resource type (letter, memo, etc.)
- `rights`, `access_rights`: Rights information (with COAR URIs)
- `is_part_of`: Collection/archive information
- `confidence_metadata`: Quality metrics

## Testing

See `tests/` directory for comprehensive unit tests.

Run tests:

```bash
pytest tests/ -v --cov=. --cov-report=html
```

Coverage target: >80%

## Troubleshooting

### "ANTHROPIC_API_KEY not set"
- Ensure your `.env` file has `ANTHROPIC_API_KEY=your-key`
- Verify the API key is valid at https://console.anthropic.com/

### "anthropic package not installed"
- Run: `pip install anthropic>=0.39.0`

### "Claude provider is not available"
- Check your API key is set correctly
- Check your Anthropic account has credits
- Verify CLAUDE_ENABLED is not set to false

### Connection issues with MCP server
- Ensure MCP server is running at `$MCP_SERVER_URL`
- Check network connectivity
- Verify `MCP_SERVER_URL` environment variable is correct

## Future Enhancements

- Add OllamaMetadataProvider for local/cost-free extraction
- Add GeminiMetadataProvider for multi-modal support
- Add OpenAIMetadataProvider as alternative
- Implement result caching for repeated extractions
- Add confidence threshold filtering
- Support for custom extraction prompts per domain
- Batch processing for multiple documents

## Development

### Project Structure

```
metadata-extraction-agent/
├── providers/
│   ├── __init__.py
│   ├── base_provider.py          # Abstract interface
│   └── claude_provider.py        # Claude implementation
├── mappers/
│   ├── __init__.py
│   ├── pala_mapper.py            # Pala schema mapper
│   └── archipelago_mapper.py     # Archipelago Commons mapper
├── tests/
│   ├── __init__.py
│   ├── test_claude_provider.py
│   ├── test_pala_mapper.py
│   ├── test_archipelago_mapper.py
│   └── test_metadata_extraction_agent.py
├── main.py                       # Agent entry point
├── requirements.txt
├── README.md
└── .env.example
```

### Adding a New Provider

1. Create `providers/new_provider.py`
2. Implement `BaseMetadataProvider` interface
3. Add to `get_provider()` method in `MetadataExtractionAgent`
4. Create tests in `tests/test_new_provider.py`
5. Update documentation

## License

Part of the Pala Platform project.
