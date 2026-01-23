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
