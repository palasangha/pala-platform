# Metadata Agent - Brainstorming & Design Notes

**Status**: Early Design Phase - Brainstorming  
**Date**: January 21, 2026  
**Purpose**: Explore clean architecture approach for metadata extraction

---

## (1) Metadata Agent — Description & What It Does

The **metadata agent** is an AI-powered extraction system that consumes digitized text (from a separate OCR/digitization pipeline) and produces rich, structured metadata conforming to defined schemas. It does NOT process images or PDFs; it only extracts and enriches metadata from already-digitized content.

**Core Functions**:
- Extract entities: people, places, organizations, events, dates
- Identify document type, structure, and relationships
- Generate summaries and key insights
- Map extracted fields to Historical Letters and Archipelago Commons schemas
- Capture out-of-schema signals (tone, sentiment, style, genre, formality, audience, etc.)
- Calculate confidence scores for all extractions
- Support user overrides with audit trails

**Why Separate from Digitization?**  
Image processing (OCR, enhancement, quality checks) is resource-intensive with different optimization goals. Splitting it cleanly allows independent scaling, faster iteration, and predictable input/output contracts.

---

## (2) Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      USER/DOCUMENT SOURCE                        │
│                       (PDF, Image, File)                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              DIGITIZATION SYSTEM (Separate)                      │
│                                                                  │
│  OCR Pipeline (e.g., Google Lens, LM Studio, Tesseract)        │
│                    OR                                            │
│  Palascribe Transcription (human/AI-assisted)                   │
│                                                                  │
│  Outputs: extracted_text + quality_score + language_detected    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    file_id + extracted_text + source_metadata
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│            METADATA AGENT (Text → Rich Metadata)                │
│                                                                  │
│  1. Validate input (enforce schema, normalize fields)           │
│  2. Analyze text (entity hints, structure, language)            │
│  3. Extract via AI (Claude|OpenAI|Ollama|Gemini)               │
│  4. Map to schemas (Historical Letters, Archipelago Commons)   │
│  5. Calculate confidence & format response                      │
│                                                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    Output: Rich Metadata JSON
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
   Archipelago        Search Index          Frontend
   Commons                                  Display
```

---

## (3) Metadata Agent — Tools, Input Schema & Output Schema

### MCP Transport
- **Protocol**: WebSocket JSON-RPC via MCP server
- **Tools exposed**:
  - `validate_input`: consumes input contract; enforces required fields, size limits; normalizes payload; returns normalized input or errors
  - `extract_metadata`: consumes validated input; routes to selected AI provider; returns raw extracted fields + confidences + `extras`
  - `map_schema`: consumes extraction output; emits `metadata.historical_document_schema` + `metadata.archipelago_commons`; preserves `metadata.extras`
  - `validate_schema` (optional): verifies final payload matches expected schemas after user overrides
  - `ping`/`health`: readiness checks

### Input Schema
```json
{
  "file_id": "string",
  "extracted_text": "string (already digitized, clean text)",
  "source_metadata": {
    "original_format": "handwritten|typed|printed|recorded",
    "language_detected": ["en", "hi"],
    "digitization_date": "ISO8601",
    "quality_score": 0.95
  },
  "user_inputs": {
    "access_level": "public|restricted|private",
    "collection_id": "optional",
    "keywords": ["user-provided", "tags"]
  },
  "ai_config": {
    "provider": "claude|openai|ollama|gemini",
    "model": "optional-override"
  }
}
```

**Field descriptions**
- `file_id`: identifier for the source asset as known to storage/repo systems.
- `extracted_text`: full clean text produced by digitization/OCR (no binary content).
- `source_metadata.original_format`: doc type hint (handwritten|typed|printed|recorded) for prompt steering.
- `source_metadata.language_detected`: languages detected upstream; used to select models/prompts.
- `source_metadata.digitization_date`: ISO8601 timestamp when text was produced.
- `source_metadata.quality_score`: float 0..1 from digitization pipeline; we propagate to confidence logic.
- `user_inputs.access_level`: sharing constraint (public|restricted|private) to respect downstream policies.
- `user_inputs.collection_id`: optional grouping/collection identifier for downstream systems.
- `user_inputs.keywords`: user-provided tags/hints (topics, people, places) to bias extraction and mapping.
- `ai_config.provider`: desired AI provider (claude|openai|ollama|gemini).
- `ai_config.model`: optional specific model name override.

### Output Schema

Refer to **Reference: Output Schema (Full)** at the end of this document.

**Summary**: Response always includes `file_id`, `metadata` (with full `historical_document_schema` per provided JSON schema, `archipelago_commons`, and `extraction_insights` for emergent metadata), `quality` (overall_confidence + per-field), `status` (success|partial|error), `errors`, `warnings`.

**Handling Out-of-Schema Metadata**: The `extraction_insights` array captures emergent signals (tone, sentiment, style, formality, audience, certainty, rhetorical_patterns, writing_quality, genre, etc.) that enrich the document but don't fit rigidly into Historical Letters catalog fields. Each insight includes category, value, confidence score, source (ai or user), and explanation. This approach preserves maximum data without forcing unnatural mappings into schema constraints.

### Schema Versioning (Simple)
- **schema_version**: Add a single SemVer string in the output payload, e.g., `"1.0.0"`.
- **Policy**: MINOR/PATCH are additive; MAJOR indicates breaking changes.
- **Default**: If the client doesn’t request a version, the agent returns the latest.
- **Optional Request Param**: `outputSchemaVersion` in `tools/invoke` arguments to pin a specific version. If unsupported, the server returns an error listing supported versions.

Example invocation args snippet:
```json
{
  "toolName": "extract_metadata",
  "arguments": {
    "outputSchemaVersion": "1.0.0"
  }
}
```

### Core Responsibilities
- ✅ Extract entities (people, places, organizations, events)
- ✅ Identify document type and structure
- ✅ Generate summaries
- ✅ Map to defined schemas
- ✅ Calculate confidence scores
- ✅ Handle user metadata overrides
- ❌ Process images/PDFs directly
- ❌ Run OCR
- ❌ Validate document quality
- ❌ Store files

---

## (4) Sequence Diagrams

### Typical Call Flow

```
Client → MCP server: validate_input(payload)
├─ Agent validates JSON shape, required fields, text size
├─ Normalizes source_metadata/user_inputs/ai_config
└─ Returns normalized payload or errors

Client → MCP server: extract_metadata(validated_payload)
├─ Agent analyzes text → build context
├─ Routes to selected AI provider (claude|openai|ollama|gemini)
├─ Extracts: entities, relationships, events, summaries, tone, sentiment, style, etc.
├─ Returns: raw extracted + confidences + extras (non-schema signals)
└─ Agent internally routes to map_schema

Agent: map_schema(raw_extracted)
├─ Maps extracted fields → Historical Letters schema format
├─ Maps extracted fields → Archipelago Commons format
├─ Preserves all extras in metadata.extras
└─ Calculates overall_confidence + per-field confidence

Agent → MCP → Client: Final Response
└─ file_id, metadata (schemas + extras), quality, status, errors, warnings
```

---

### 1. Text Quality & Trust
**Question**: What if extracted text has OCR errors?

**Options**:
- A) Metadata Agent accepts text as-is, works with what it gets
- B) Metadata Agent has confidence scores reflecting text quality
- C) User can specify text quality/confidence level in input

**Thought**: Combination of B + C. If digitization system reports low quality, metadata agent reflects that in confidence scores.

---

### 2. AI Extraction Granularity
**Question**: Should we extract at different detail levels?

**Options**:
- A) Always detailed extraction (people, organizations, events, etc.)
- B) Configurable detail level (basic vs detailed)
- C) Adaptive based on text length/quality

**Thought**: Option B makes sense. Some documents just need basic metadata, others need rich detail. Input could come from `user_inputs.keywords` plus a new optional `detail_level` flag (basic|detailed) in `user_inputs`.

---

### 3. User Input Handling
**Question**: How much can users override AI extraction?

**Options**:
- A) Can only add metadata (keywords, collection), not override
- B) Can override any field extracted by AI
- C) Can override but we flag it with audit trail

**Thought**: Allow overrides on any field (Option B) and expose `validate_schema` to ensure the final payload still matches schemas; keep audit trail of overrides.

---

### 4. External File References
**Question**: Does metadata agent need to know about file storage?

**Options**:
- A) No - it only works with text, returns metadata
- B) Yes - needs to generate S3/MinIO URLs
- C) Optional - if file_path provided, can generate URLs

**Thought**: Option A is cleaner. File storage is separate concern. Metadata is independent.

Actually, reconsider: Option C might be useful for Archipelago integration. If we know where file is stored, we can reference it. But not required.

---

### 5. Streaming vs Batch
**Question**: Process one document or batch?

**Options**:
- A) Single document endpoint only
- B) Batch processing capability
- C) Both, with async support

**Thought**: Start with A (single document), design so B is easy to add.

---

## 🎯 Next Decisions (confirmed/clarified)

1. Metadata agent should NOT process images directly — **Confirmed**
2. Input is always digitized text (from separate system) — **Confirmed**
3. Component breakdown: 4 components — **Confirmed**
4. File reference generation: question unclear; keep TBD for now
5. MVP scope: decide after this doc is finalized

---

## 🎨 Technology Approach

### AI Providers
**Primary**: Claude (best quality reasoning)  
**Fallback**: OpenAI (GPT-4)  
**Local**: Ollama (privacy-focused)  
**Alternative**: Gemini

### Extraction Strategy
- Structured prompts with explicit JSON output
- Temperature: 0.1 (prioritize accuracy)
- Prompt engineering iterative based on evals

### Schema Support
- Historical Letters schema (primary)
- Archipelago Commons format (secondary)
- Extensible for future schemas; extras bucket ensures no data loss

---

## 📝 Open Questions

1. **Text Quality Signals**: Should digitization system provide confidence/quality metrics? → **Yes. Use quality_score from digitization.**
2. **File Storage**: Should metadata agent know about file paths? → **No. Keep storage concerns external unless provided for reference.**
3. **Archipelago Integration**: How tightly coupled should this be? → **We need to support it to store in external systems.**
4. **Performance Targets**: What's acceptable latency? (30s? 60s?) → **Open: propose starting target?**
5. **Concurrency**: How many simultaneous requests should it support? → **Yes, large batches; parallelism needed (multi-job later).**
6. **Caching**: Should we cache extracted metadata or re-extract each time? → **Not sure yet.**

---

## 🚀 Proposed Next Steps

1. **Validate Architecture**: Review separation of concerns
2. **Finalize Input/Output**: Define exact JSON schemas
3. **Design Phase 1**: Pick 3-4 key extraction tasks
4. **Plan Prompts**: Develop AI extraction prompt templates
5. **Build MVP**: Implement 4 components with one AI provider
6. **Test & Iterate**: Refine based on results

---

## 📚 References to Existing Code

- OCR Processor: `packages/processors/OCR_metadata_extraction/`
- Sample Agent: `packages/agents/sample-agent/`
- Historical Letters Schema: From provided JSON file
- Archipelago Integration: `backend/app/services/archipelago_service.py`

---

## Reference: Output Schema (Full)

```json
{
  "file_id": "string",
  "metadata": {
    "schema_version": "1.0.0",
    "historical_document_schema": {
      "metadata": {
        "id": "string - unique identifier",
        "collection_id": "string - collection identifier",
        "document_type": "letter|memo|telegram|fax|email|invitation",
        "storage_location": {
          "archive_name": "string",
          "collection_name": "string",
          "box_number": "string",
          "folder_number": "string",
          "digital_repository": "string (URL or ID)"
        },
        "digitization_info": {
          "date": "YYYY-MM-DD",
          "operator": "string",
          "equipment": "string",
          "resolution": "string",
          "file_format": "PDF|JPEG|etc"
        },
        "access_level": "public|restricted|private"
      },
      "document": {
        "date": {
          "creation_date": "YYYY-MM-DD",
          "sent_date": "YYYY-MM-DD",
          "received_date": "YYYY-MM-DD"
        },
        "reference_number": "string",
        "languages": ["array of language codes"],
        "physical_attributes": {
          "size": "string (dimensions)",
          "material": "string (paper type)",
          "condition": "string",
          "letterhead": "string (description)",
          "pages": "integer"
        },
        "correspondence": {
          "sender": {
            "name": "string",
            "title": "string",
            "affiliation": "string",
            "location": "string",
            "contact_info": {
              "address": "string",
              "telephone": "string",
              "fax": "string",
              "email": "string"
            },
            "biography": "string"
          },
          "recipient": {
            "name": "string",
            "title": "string",
            "affiliation": "string",
            "location": "string",
            "contact_info": {
              "address": "string",
              "telephone": "string",
              "fax": "string",
              "email": "string"
            },
            "biography": "string"
          },
          "cc": [
            {
              "name": "string",
              "title": "string",
              "affiliation": "string"
            }
          ]
        }
      },
      "content": {
        "full_text": "string - complete transcription",
        "summary": "string - brief summary",
        "salutation": "string - opening greeting",
        "body": ["array of paragraphs"],
        "closing": "string - closing statement",
        "signature": "string - description of signature",
        "attachments": ["array of attachment descriptions"],
        "annotations": [
          {
            "text": "string",
            "location": "string (on document)",
            "author": "string (if known)"
          }
        ]
      },
      "analysis": {
        "keywords": ["array of keywords"],
        "subjects": ["array of subject categories"],
        "events": [
          {
            "name": "string",
            "date": "YYYY-MM-DD",
            "location": "string",
            "description": "string"
          }
        ],
        "locations": [
          {
            "name": "string",
            "type": "country|city|institution|building|other",
            "coordinates": {
              "latitude": "number",
              "longitude": "number"
            }
          }
        ],
        "people": [
          {
            "name": "string",
            "role": "string",
            "affiliation": "string",
            "biography": "string"
          }
        ],
        "organizations": [
          {
            "name": "string",
            "type": "string",
            "location": "string",
            "description": "string"
          }
        ],
        "historical_context": "string",
        "significance": "string",
        "relationships": [
          {
            "document_id": "string",
            "relationship_type": "response_to|mentioned_in|precedes|follows|references",
            "description": "string"
          }
        ]
      }
    },
    "archipelago_commons": {
      "title": "string",
      "description": "string",
      "creator": ["array of creator names"],
      "contributor": ["array of contributor names"],
      "subject": ["array of subject keywords"],
      "date": "YYYY-MM-DD",
      "type": "string",
      "identifier": "string",
      "rights": "string (rights statement)",
      "language": "string"
    },
    "extraction_insights": [
      {
        "category": "tone|sentiment|style|formality|genre|rhetorical_patterns|audience_level|certainty|writing_quality|other",
        "value": "string|number|object",
        "confidence": 0.0,
        "source": "ai|user",
        "explanation": "string - why this insight was extracted"
      }
    ]
  },
  "quality": {
    "overall_confidence": 0.92,
    "digitization_quality_input": 0.95,
    "extraction_by_field": {
      "sender_name": 0.98,
      "recipient_name": 0.96,
      "date": 0.94,
      "subject": 0.88,
      "locations": 0.85,
      "people": 0.82,
      "tone": 0.79
    }
  },
  "status": "success|partial|error",
  "errors": ["array of error messages if any"],
  "warnings": ["array of warning messages if any"],
  "audit_trail": {
    "processed_at": "ISO8601 timestamp",
    "ai_provider_used": "claude|openai|ollama|gemini",
    "model": "specific model name",
    "user_overrides": [
      {
        "field_path": "string (e.g., 'metadata.historical_document_schema.document.correspondence.sender.name')",
        "original_value": "value from AI extraction",
        "override_value": "value provided by user",
        "timestamp": "ISO8601"
      }
    ]
  }
}
```

---

**This is a living document - update as we refine the design**

