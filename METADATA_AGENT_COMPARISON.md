# Metadata Agent Comparison

## Overview
- **metadata-agent** (located at `packages/agents/metadata-agent/`): Previous implementation focused on specific structured extraction tasks
- **metadata-extraction-agent** (located at `packages/agents/metadata-extraction-agent/`): Current implementation designed for unified, provider-agnostic metadata extraction with support for multiple output schemas (Pala, Archipelago)

## Key Architectural Differences

### 1. **Scope & Purpose**

#### metadata-agent (Old)
- **4 specialized tools:**
  1. `extract_document_type` - Classify document (letter, memo, telegram, etc.)
  2. `extract_storage_info` - Parse archive/collection/box/folder references
  3. `extract_digitization_metadata` - Extract scanning date, operator, equipment
  4. `determine_access_level` - Classify access level (public/restricted/private)
- **Domain-Specific**: Designed for archival/museum/historical document workflows
- **Tool-Centric**: Each tool is a separate concern with own tool handlers

#### metadata-extraction-agent (New)
- **1 unified tool:**
  - `extract_metadata` - Single endpoint that supports multiple providers and output schemas
- **Provider-Agnostic**: Pluggable architecture supports Claude, Ollama, and extensible for Gemini, OpenAI
- **Schema-Flexible**: Supports multiple output formats (Pala, Archipelago, combined)

### 2. **Provider Architecture**

#### metadata-agent (Old)
- Uses **local tool handlers** in `tools/` directory:
  - `DocumentClassifier` (Ollama)
  - `StorageExtractor` (Ollama)
  - `AccessDeterminer` (Ollama)
- Each tool class directly imports Ollama and calls it
- **No abstraction layer** - tightly coupled to Ollama

#### metadata-extraction-agent (New)
- **Provider abstraction layer** with interface pattern:
  - `BaseMetadataProvider` (interface)
  - `ClaudeMetadataProvider` (implements BaseMetadataProvider)
  - `OllamaMetadataProvider` (implements BaseMetadataProvider)
  - Extensible for future providers (Gemini, OpenAI, etc.)
- **Single extraction endpoint** that dispatches to provider
- **Unified schema handling** with mappers for output normalization

### 3. **Ollama Usage**

#### metadata-agent (Old)
**Tool Classes in `tools/` folder:**
```python
# DocumentClassifier uses Ollama directly
async def classify(text, ocr_confidence):
    # Direct Ollama call
```

#### metadata-extraction-agent (New)
**Provider Pattern:**
```python
class OllamaMetadataProvider(BaseMetadataProvider):
    async def extract_metadata(ocr_text, language, document_context, custom_prompt):
        # Unified extraction with configurable prompt
        # Returns structured data that mappers normalize
```

### 4. **Schema Mapping**

#### metadata-agent (Old)
- **No schema mapping** - returns raw tool outputs
- No normalization to standard schemas (Pala, Archipelago)
- Each tool returns its own structure

#### metadata-extraction-agent (New)
- **Mappers for output normalization:**
  - `PalaMapper` - Maps to Pala schema v1.0.0
  - `ArchipelagoMapper` - Maps to Archipelago Commons standard
- **Confidence scores** extracted and calculated across all fields
- **Extraction metadata** (timestamp, processing time, model used) automatically tracked

### 5. **Parameter Handling**

#### metadata-agent (Old)
- Each tool takes specific parameters (text, file_path, metadata)
- No unified interface for context/custom prompts
- Limited control over extraction behavior

#### metadata-extraction-agent (New)
- **Unified parameters** for all providers:
  - `text` - Required OCR text
  - `model` - Provider selection (claude/ollama/gemini/openai)
  - `output_type` - Schema selection (pala/archipelago/combined)
  - `language` - ISO language code
  - `document_context` - Context hint for extraction
  - `custom_prompt` - Override default extraction prompt
  - `schema_version` - Pin to specific schema version

### 6. **Response Structure**

#### metadata-agent (Old)
```python
# Each tool returns different structure
{
    "document_type": "letter",
    "confidence": 0.95,
    "reasoning": "..."
}
```

#### metadata-extraction-agent (New)
```python
{
    "schema_version": "1.0.0",
    "extraction_metadata": {
        "model_used": "ollama",
        "timestamp": "2026-03-04T...",
        "processing_time_ms": 1234,
        "input_length": 5000
    },
    "confidence_scores": {
        "overall": 0.87,
        "field_name": 0.92,
        ...
    },
    "pala_metadata": {...},        # if output_type includes pala
    "archipelago_metadata": {...}, # if output_type includes archipelago
    "extracted_fields": {...}      # if output_type is "combined"
}
```

## Why Ollama Metadata Might Not Be Generating

### Potential Issues in metadata-extraction-agent:

1. **Provider Availability Check**
   - OllamaMetadataProvider checks `OLLAMA_ENABLED` env var (defaults to "true")
   - If Ollama service not running at `http://localhost:11434`, it won't detect it
   - Model availability check might fail if model not in Ollama

2. **Model Configuration**
   - Default model is `minicpm-v` - must be available in Ollama
   - If wrong model name, extraction fails

3. **Prompt Format**
   - Ollama prompt builds JSON schema to extract
   - JSON parsing might fail if Ollama response format doesn't match regex pattern
   - Response parsing uses regex to find JSON in text - could fail with certain model outputs

4. **Request Timeout**
   - Default timeout is 120 seconds
   - If Ollama is slow or overloaded, might timeout

5. **Environment Variable Configuration**
   - `OLLAMA_BASE_URL` (defaults to http://localhost:11434)
   - `OLLAMA_MODEL` (defaults to minicpm-v)
   - `OLLAMA_ENABLED` (defaults to true)

### What metadata-agent Was Doing Better:

1. **Domain-Specific Tools** - Separate, focused extraction tools for specific document properties
2. **Multiple Concurrent Extractions** - Could run document type + storage + digitization + access level in parallel
3. **Fallback Mechanisms** - Each tool had built-in fallback returns on error

## Recommendations

### To Debug Ollama Metadata Generation:

1. **Check Ollama connectivity:**
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. **Check if provider is available:**
   - Look at logs for "✓ Ollama metadata provider initialized" or "✗ Ollama provider:"
   - Check `OLLAMA_ENABLED`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`

3. **Test Ollama extraction directly:**
   ```python
   from providers.ollama_provider import OllamaMetadataProvider
   provider = OllamaMetadataProvider()
   result = await provider.extract_metadata(ocr_text="sample text")
   ```

4. **Check JSON parsing:**
   - Add debug logging in `_parse_response()` to see raw Ollama output
   - Verify regex pattern matches response format

### Potential Solutions:

1. **Hybrid approach**: Keep both agents - use metadata-agent for domain-specific tasks, metadata-extraction-agent for unified extraction
2. **Enhance OllamaMetadataProvider**: Add more robust parsing, fallback schemas, better error recovery
3. **Tool composition**: Have metadata-extraction-agent call out to storage-agent for integration
4. **Provider selection**: Ensure Ollama is selected and available when making requests
