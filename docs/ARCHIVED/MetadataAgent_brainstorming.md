# Metadata Agent - Design Specification

**Status**: Design Finalized - Ready for Implementation  
**Date**: January 23, 2026  
**Purpose**: Metadata extraction agent that produces structured metadata from OCR text

---

## (1) Overview

The **Metadata Agent** is an AI-powered extraction system that takes OCR-extracted text as input and produces rich, structured metadata conforming to defined schemas. It operates as a stateless service exposed via MCP (Model Context Protocol) for consistent access across all clients.

**Core Functions**:
- Extract entities: people, places, organizations, events, dates
- Identify document type, structure, and relationships
- Generate summaries and key insights
- Map extracted fields to Pala Metadata and Archipelago Commons schemas
- Capture out-of-schema signals (tone, sentiment, style, etc.)
- Calculate confidence scores for all extractions
- Support configurable output types (Pala, Archipelago, or combined)

**Design Principles**:
- **Stateless**: No shared state between calls; safe for parallel execution
- **Clean separation**: OCR/digitization is separate; agent only processes text
- **MCP-first**: All access goes through MCP server for consistency
- **Schema-driven**: Output conforms to versioned schemas

---

## (2) Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    OCR PIPELINE (Existing)                       │
│                                                                  │
│  Image/PDF → OCR Provider → Extracted Text                      │
│  (Google Lens, LangChain, Ollama, etc.)                        │
│                                                                  │
│  Output: extracted_text + language + confidence                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ OCR text
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MCP SERVER                                  │
│                   (ws://localhost:3000)                         │
│                                                                  │
│  Tool: extract_metadata                                         │
│  ├─ Input: ocr_text, model, output_type                        │
│  ├─ Routes to Metadata Agent                                    │
│  └─ Returns: structured metadata JSON                           │
│                                                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ invoke tool
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│          METADATA AGENT (packages/agents/metadata-agent/)        │
│                                                                  │
│  Stateless Python module                                         │
│  1. Take OCR text input                                          │
│  2. Call AI provider (Claude/Ollama/etc) with optimized prompt │
│  3. Extract metadata fields                                      │
│  4. Map to schemas based on output_type                         │
│  5. Return JSON with schema_version + confidence scores         │
│                                                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    Structured Metadata JSON
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
   OCR Chains         Web Dashboard       DataMapper
   (bulk)              (single doc)      (Archipelago export)
```

**Key Design Decisions:**
- **MCP-first**: All clients (chains, dashboard, exporters) call metadata agent via MCP
- **Stateless**: Agent has no shared state; multiple instances can run in parallel
- **Bulk via Chains**: NSQ workers call MCP tool for each document in parallel
- **Single endpoint**: One `extract_metadata` tool with `output_type` parameter

---

## (3) MCP Tool Interface

### Tool: `extract_metadata`

Single unified tool for metadata extraction with flexible output formatting.

**Input Parameters**:
```typescript
{
  ocr_text: string,              // Required: OCR-extracted text
  model: "claude" | "ollama" | "gemini" | "openai",  // Required: AI provider
  output_type: "pala" | "archipelago" | "combined",  // Required: what to return
  custom_prompt?: string,        // Optional: override default extraction prompt
  language?: string,             // Optional: language code (e.g., "en", "hi")
  document_context?: string,     // Optional: "historical_letter", "monastery_record", etc.
  schema_version?: string        // Optional: pin to specific output version (e.g., "1.0.0")
}
```

### Output Schema

Refer to Pala and Archipelago schema definitions below.

**Structure**:
```json
{
  "schema_version": "1.0.0",
  "extraction_metadata": {
    "model_used": "claude",
    "timestamp": "2026-01-23T10:30:00Z",
    "processing_time_ms": 2340,
    "input_length": 5420
  },
  "confidence_scores": {
    "overall": 0.92,
    "sender": 0.95,
    "recipient": 0.88,
    "date": 0.85,
    "document_type": 0.90
  },
  "pala_metadata": {
    /* Only included if output_type is "pala" or "combined" */
    /* Full schema defined below */
  },
  "archipelago_metadata": {
    /* Only included if output_type is "archipelago" or "combined" */
    /* Full schema defined below */
  }
}
```

**Output Type Behavior**:
- `"pala"`: Returns `schema_version` + `extraction_metadata` + `confidence_scores` + `pala_metadata`
- `"archipelago"`: Returns `schema_version` + `extraction_metadata` + `archipelago_metadata`
- `"combined"`: Returns all sections (full output)

### Schema Versioning
- Current version: `1.0.0` (SemVer)
- MINOR/PATCH: Additive changes (new optional fields)
- MAJOR: Breaking changes (removed/renamed fields)
- Optional request parameter: `schema_version` to pin specific version
- Default: Returns latest version if not specified

### Core Responsibilities
- ✅ Extract entities (people, places, organizations, events)
- ✅ Identify document type and structure
- ✅ Generate summaries
- ✅ Map to Pala and Archipelago schemas
- ✅ Calculate confidence scores
- ❌ Process images/PDFs directly
- ❌ Run OCR
- ❌ Validate document quality
- ❌ Store files

---

## (4) Sequence Diagrams

### Single-Tool Call Flow

```
Client → MCP server: extract_metadata({
  ocr_text,
  model,
  output_type,
  custom_prompt?,
  language?,
  document_context?
})
├─ Agent routes to selected AI provider (claude|openai|ollama|gemini)
├─ Executes extraction with custom or default prompt
├─ Extracts: entities, relationships, dates, summaries, document type
├─ Maps to requested schema(s) based on output_type parameter
├─ Calculates confidence scores per field
└─ Returns structured output

Agent → Client: Response
└─ schema_version, extraction_metadata, confidence_scores, requested schema(s)
```

### Bulk Processing via OCR Chains

```
User → Web Dashboard: Creates OCR chain with metadata extraction step
Dashboard → Backend: POST /chains with steps including "metadata_agent"
Backend → NSQ: Publishes chain job to queue

NSQ Workers (parallel):
├─ Worker 1: Processes document 1
│   └─ MCP Client → extract_metadata(ocr_text, model="claude", output_type="combined")
├─ Worker 2: Processes document 2
│   └─ MCP Client → extract_metadata(ocr_text, model="gemini", output_type="pala")
└─ Worker N: Processes document N
    └─ MCP Client → extract_metadata(ocr_text, model="ollama", output_type="archipelago")

Each worker:
├─ Receives metadata response from agent
├─ Stores result in database
└─ Optionally exports to Archipelago Commons
```

---

## (5) Pala Metadata Schema

Based on "Historical Letters Collection Schema" (see attached schema file).

```json
{
  "pala_metadata": {
    "metadata": {
      "id": "string",
      "collection_id": "string",
      "document_type": "letter|memo|telegram|fax|email|invitation",
      "access_level": "public|restricted|private"
    },
    "document": {
      "date": {
        "creation_date": "YYYY-MM-DD",
        "sent_date": "YYYY-MM-DD",
        "received_date": "YYYY-MM-DD"
      },
      "languages": ["en", "hi"],
      "correspondence": {
        "sender": {
          "name": "string",
          "title": "string",
          "affiliation": "string",
          "location": "string",
          "biography": "string"
        },
        "recipient": {
          "name": "string",
          "title": "string",
          "affiliation": "string",
          "location": "string",
          "biography": "string"
        }
      }
    },
    "content": {
      "summary": "string",
      "salutation": "string",
      "body": ["paragraph1", "paragraph2"],
      "closing": "string",
      "attachments": ["string"]
    },
    "analysis": {
      "keywords": ["string"],
      "subjects": ["string"],
      "people": [
        {
          "name": "string",
          "role": "string",
          "affiliation": "string"
        }
      ],
      "locations": [
        {
          "name": "string",
          "type": "country|city|institution|building|other"
        }
      ],
      "organizations": [
        {
          "name": "string",
          "type": "string"
        }
      ],
      "events": [
        {
          "name": "string",
          "date": "YYYY-MM-DD",
          "description": "string"
        }
      ],
      "historical_context": "string",
      "significance": "string"
    }
  }
}
```

---

## (6) Archipelago Commons Metadata Schema

Based on Archipelago Digital Objects (ADO) format used by `data_mapper.py`.

```json
{
  "archipelago_metadata": {
    "label": "string",
    "type": "DigitalDocument|Image|Video|Audio",
    "description": "string",
    "note": "string (OCR text or notes)",
    "language": ["English", "Hindi"],
    "date_created": "ISO8601",
    "creator": "string",
    "owner": "string",
    "publisher": "string",
    "rights": "string",
    "ismemberof": ["collection_id"],
    "ispartof": ["parent_node_id"],
    "subjects_local": "string (comma-separated keywords)",
    "as:generator": {
      "type": "Service",
      "name": "metadata-agent",
      "version": "1.0.0",
      "datetime": "ISO8601",
      "model": "claude|ollama|gemini|openai"
    },
    "as:document": {
      "urn:uuid:{uuid}": {
        "url": "s3://bucket/path/to/file",
        "name": "filename.pdf",
        "type": "Document",
        "dr:fid": "drupal_file_id",
        "dr:uuid": "uuid",
        "dr:for": "documents",
        "dr:filesize": 123456,
        "dr:mimetype": "application/pdf",
        "checksum": "md5_hash",
        "crypHashFunc": "md5"
      }
    },
    "documents": ["file_id"],
    "images": [],
    "videos": [],
    "audios": [],
    "ap:entitymapping": {
      "entity:file": ["documents", "images", "videos", "audios"],
      "entity:node": ["ismemberof", "ispartof"]
    }
  }
}
```

---

## (7) Implementation Plan

**Status**: Ready for development  
**Target**: Build as new `metadata-extraction-agent` (separate from existing `metadata-agent`)  
**Approach**: Follow design spec exactly; create fresh implementation without modifying existing code

### Directory Structure

```
packages/agents/metadata-extraction-agent/
├── providers/
│   ├── __init__.py
│   ├── base_provider.py              # Abstract base class for all providers
│   └── claude_provider.py            # Claude implementation
├── mappers/
│   ├── __init__.py
│   ├── pala_mapper.py                # Maps to Pala schema v1.0.0
│   └── archipelago_mapper.py         # Maps to Archipelago Commons schema
├── tests/
│   ├── __init__.py
│   ├── test_claude_provider.py
│   ├── test_pala_mapper.py
│   ├── test_archipelago_mapper.py
│   └── test_metadata_extraction_agent.py
├── main.py                           # MetadataExtractionAgent class
├── requirements.txt
├── README.md
└── .env.example
```

### Implementation Phases

#### Phase 1: Core Implementation (7 files)

**providers/base_provider.py**
- Abstract `BaseMetadataProvider` class
- Define interface: `async extract_metadata(ocr_text, language, document_context, custom_prompt) -> Dict`
- All providers must implement this interface

**providers/claude_provider.py**
- `ClaudeMetadataProvider(BaseMetadataProvider)`
- Initialize Claude client with `ANTHROPIC_API_KEY` env var
- Call Claude API with extraction prompt
- Parse JSON response
- Return raw extracted data with confidence scores (0.0-1.0) for all fields
- Handle errors gracefully

**mappers/pala_mapper.py**
- `PalaMapper` class with static method `map_extracted_data(extracted_data) -> Dict`
- Map extracted fields to Pala schema v1.0.0 (section 5 of this doc)
- Structure: `document_metadata`, `parties`, `places`, `storage`, `access`, `content`, `quality_metrics`, `metadata`
- Preserve all confidence scores
- Calculate overall confidence average

**mappers/archipelago_mapper.py**
- `ArchipelagoMapper` class with static method `map_extracted_data(extracted_data) -> Dict`
- Map extracted fields to Archipelago Commons schema (section 6 of this doc)
- Include confidence metadata with high/low confidence field tracking
- Map access levels to COAR access rights URIs
- Support museum/archive integration

**main.py - MetadataExtractionAgent**
- `MetadataExtractionAgent` class
- `__init__()`: Initialize Claude client, set up MCP connection
- `async extract_metadata(ocr_text, model, output_type, language, document_context, custom_prompt, schema_version) -> Dict`
  - Route to appropriate provider based on `model` parameter
  - Call provider's `extract_metadata()`
  - Apply appropriate mapper(s) based on `output_type`:
    - "pala": Use PalaMapper
    - "archipelago": Use ArchipelagoMapper
    - "combined": Use both mappers, include raw extracted_fields
  - Return structured response per section 3 output schema
- `get_provider(model)`: Route to provider by name (supports future extensibility)
- `get_tool_definitions()`: Return MCP tool definition for `extract_metadata`
- `async handle_tool_invocation()`: Parse MCP requests and route to extract_metadata
- `async run()`: Main agent loop - connect to MCP server, register tool, listen for invocations

#### Phase 2: Configuration (2 files)

**requirements.txt**
```
anthropic>=0.39.0
websockets>=11.0
python-dotenv>=0.19.0
```

**README.md**
- Setup instructions (install dependencies, set ANTHROPIC_API_KEY)
- Usage examples (MCP JSON-RPC calls)
- Output schema examples
- Troubleshooting guide

#### Phase 3: Unit Tests (5 test files, >80% coverage)

**tests/test_claude_provider.py**
- Test Claude client initialization with/without API key
- Test `extract_metadata()` with valid OCR text
- Test JSON parsing of Claude response
- Test confidence score generation (all fields 0.0-1.0)
- Test error handling (API errors, malformed responses, empty input)
- Mock Claude API for deterministic testing

**tests/test_pala_mapper.py**
- Test `map_extracted_data()` with sample extracted data
- Verify all required Pala schema fields present
- Test confidence score preservation
- Test overall confidence calculation
- Test edge cases (missing fields, null values, empty arrays)

**tests/test_archipelago_mapper.py**
- Test `map_extracted_data()` with sample extracted data
- Verify Archipelago Commons schema compliance
- Test COAR access rights URI mapping
- Test high/low confidence field categorization
- Test provenance metadata

**tests/test_metadata_extraction_agent.py**
- Test agent initialization with MCP connection
- Test `get_provider()` routing (Claude, extensible for others)
- Test `extract_metadata()` with different output_type values
- Test tool registration and invocation
- Test error handling and edge cases

**Integration Test**
- End-to-end test with real Claude API (or mocked)
- Test full flow: OCR text → Claude extraction → mapping → response

#### Phase 4: Dashboard Updates (1 file)

**apps/web/components/Dashboard.tsx**
- Add tool-specific placeholders for `extract_metadata`:
  ```json
  {
    "ocr_text": "Dear Sir,\n\nI write to you from the archives of the Pala Sangha monastery, dated 15th March 1892. This letter concerns...",
    "model": "claude",
    "output_type": "combined",
    "language": "en",
    "document_context": "historical_letter"
  }
  ```
- Add parameter hints:
  - Required: `ocr_text`, `model`, `output_type`
  - Optional: `language`, `document_context`, `custom_prompt`, `schema_version`
  - Model options: "claude" (+ future: "ollama", "gemini", "openai")
  - Output_type options: "pala", "archipelago", "combined"
- Show realistic historical document examples
- Display response structure with confidence scores

#### Phase 5: MCP Server Integration (updates to existing)

**packages/mcp-server/src/handlers.ts** (if needed)
- Register new agent: `metadata-extraction-agent`
- Ensure tool routing works for `extract_metadata`
- May not need changes if using same MCP protocol

### Client Usage

**WebSocket JSON-RPC Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/invoke",
  "params": {
    "toolName": "extract_metadata",
    "agentId": "metadata-extraction-agent",
    "arguments": {
      "ocr_text": "Dear Sir,\n\nI write to you from...",
      "model": "claude",
      "output_type": "combined",
      "language": "en",
      "document_context": "historical_letter"
    }
  },
  "id": "request-123"
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "schema_version": "1.0.0",
    "extraction_metadata": {
      "model_used": "claude",
      "timestamp": "2026-02-23T10:30:00Z",
      "processing_time_ms": 2340,
      "input_length": 5420
    },
    "confidence_scores": {
      "overall": 0.92,
      "sender": 0.95,
      "recipient": 0.88,
      "date": 0.85,
      "document_type": 0.90
    },
    "pala_metadata": { /* ... */ },
    "archipelago_metadata": { /* ... */ },
    "extracted_fields": { /* raw extracted data */ }
  },
  "id": "request-123"
}
```

### Key Design Decisions

1. **Separate agent**: New `metadata-extraction-agent` keeps it distinct from existing `metadata-agent` (untouched)
2. **Pluggable providers**: Design with `BaseMetadataProvider` interface for easy addition of Ollama, Gemini, OpenAI later
3. **Schema-agnostic**: Single agent supports multiple output schemas via `output_type` parameter
4. **Confidence scores**: All extracted fields include 0.0-1.0 confidence for quality assessment
5. **No side effects**: Stateless implementation, safe for parallel execution
6. **Clean separation**: Providers handle extraction, mappers handle schema transformation

### Testing Strategy

- Unit tests for each component with >80% coverage
- Mock Claude API for deterministic testing
- Integration tests with real historical documents
- Manual testing via Dashboard

### Future Extensions

- Add OllamaMetadataProvider for local/cost-free extraction
- Add GeminiMetadataProvider for multi-modal support
- Add OpenAIMetadataProvider as alternative
- Support custom extraction prompts per document context
- Add confidence threshold filtering
- Implement caching for repeated extractions
