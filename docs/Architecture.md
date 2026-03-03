# Pala Platform Architecture

## Overview

Pala Platform is a **core infrastructure layer** providing:
- **MCP Server**: Central communication hub for agents
- **Storage Agent**: Unified database with generic extraction storage
- **Metadata Extractor Agent**: Optional AI-powered metadata enrichment

**Key Principle**: Pala Platform does NOT provide domain-specific business logic (OCR, transcription, etc.). Instead, external web applications handle their own processing and use the Storage Agent as their integration point.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Pala Platform Core                    │
│                                                          │
│  ┌──────────────┐    ┌──────────────┐   ┌────────────┐ │
│  │  MCP Server  │◄──►│Storage Agent │   │ Metadata   │ │
│  │  (WS Hub)    │    │ (Unified DB) │   │ Extractor  │ │
│  └──────────────┘    └──────────────┘   └────────────┘ │
│         ▲                    ▲                  ▲        │
└─────────┼────────────────────┼──────────────────┼────────┘
          │                    │                  │
          │                    │                  │
┌─────────▼────────┐  ┌────────▼──────┐  ┌───────▼────────┐
│   OCR Web App    │  │ Transcription │  │  Doc Convert   │
│  (own logic/DB)  │  │  (own logic)  │  │  (own logic)   │
│  Calls:          │  │  Calls:       │  │  Calls:        │
│  store_extraction│  │  store_extract│  │  store_extract │
└──────────────────┘  └───────────────┘  └────────────────┘
```

## Core Components

### 1. MCP Server
- **Technology**: Node.js + TypeScript
- **Protocol**: JSON-RPC 2.0 over WebSocket
- **Responsibilities**:
  - Agent registration and discovery
  - Tool routing and invocation
  - Request tracing with correlation IDs
  - Optional JWT authentication
  - Heartbeat monitoring

### 2. Storage Agent
- **Technology**: Python + SQLite
- **Tools Provided**:
  - `store_extraction()` - Universal write endpoint for any extraction type
  - `retrieve_extraction()` - Get single extraction by ID
  - `list_extractions()` - Query with filters (source_type, source_id)
  - `store_document()` - Legacy document storage
  - `retrieve_document()` - Legacy document retrieval
  - `list_documents()` - Legacy document listing

**Database Schema:**
```sql
unified_extractions (
  id UUID PRIMARY KEY,
  source_type VARCHAR,      -- 'ocr', 'transcription', 'translation', etc.
  source_id UUID,            -- Reference to source document/file
  data TEXT,                 -- Actual extracted content (text or JSON)
  data_type VARCHAR,         -- 'text', 'json', 'binary'
  metadata JSONB,            -- Tool-specific metadata
  provider VARCHAR,          -- 'tesseract', 'whisper', 'ollama', etc.
  confidence FLOAT,          -- Extraction confidence score
  created_by VARCHAR,        -- Agent/user identifier
  created_at TIMESTAMP
)
```

### 3. Metadata Extractor Agent
- **Technology**: Python + Anthropic Claude API
- **Tools Provided**:
  - `extract_metadata()` - Extract structured metadata from text content
- **Use Case**: Optional enrichment for any extraction (OCR results, transcriptions, etc.)

## External Web Applications

External apps are **independent applications** that:
1. Have their own UI, business logic, and local database
2. Connect to MCP Server via WebSocket
3. Use Storage Agent tools to persist results in Pala Platform's unified DB
4. Optionally call Metadata Extractor for enrichment

**Example: OCR Web App**
```
packages/processors/OCR_metadata_extraction/
├── backend/          (Flask API with OCR business logic)
├── frontend/         (React UI for uploading images)
└── storage/          (Local temp file storage)

Flow:
1. User uploads image to OCR frontend
2. Frontend sends to OCR backend
3. Backend runs OCR (Tesseract/Ollama/LMStudio)
4. Backend calls MCP: storage_agent.store_extraction({
     source_type: "ocr",
     source_id: "file-uuid",
     data: "extracted text...",
     provider: "ollama",
     confidence: 0.92
   })
5. Pala Platform's unified DB now has the extraction
6. Other apps/chatbot can query this data
```

## Integration Pattern

Any web app can integrate with Pala Platform by:

```python
# 1. Connect to MCP Server
ws = websockets.connect("ws://localhost:3000")

# 2. Call storage-agent tools
result = await ws.send({
  "jsonrpc": "2.0",
  "method": "tools/invoke",
  "params": {
    "agentId": "storage-agent",
    "toolName": "store_extraction",
    "arguments": {
      "source_type": "transcription",
      "source_id": "audio-123",
      "data": "transcribed text...",
      "data_type": "text",
      "metadata": {"duration": 120, "language": "en"},
      "provider": "whisper",
      "confidence": 0.95,
      "created_by": "transcription-app"
    }
  }
})
```

## Benefits of This Architecture

✅ **Decoupled**: Each app is independent, can be developed/deployed separately  
✅ **Unified Data**: All extractions flow into single Pala Platform DB  
✅ **Extensible**: New apps integrate by just calling `store_extraction()`  
✅ **No Duplication**: Apps don't need to implement their own storage/metadata layers  
✅ **Flexible**: Apps can use any tech stack (Python, Node, Go, etc.)  
✅ **Optional Services**: Apps choose which Pala Platform services to use

## Technology Stack

**Core Platform:**
- MCP Server: Node.js, TypeScript, WebSocket, JSON-RPC 2.0
- Storage Agent: Python 3.14, SQLite, WebSockets
- Metadata Extractor: Python 3.14, Anthropic Claude API

**External Apps (Example):**
- OCR App: Python Flask backend, React frontend, Tesseract/Ollama/LMStudio
- Future apps: Any language, any framework

## Deployment

**Core Services (Required):**
```bash
./start-dev.sh
```
Starts: MCP Server, Storage Agent, Metadata Extractor, Web Dashboard

**External Apps (Optional):**
Each app has its own startup:
```bash
cd packages/processors/OCR_metadata_extraction
./start.sh
```

## Single Source of Truth

Pala Platform's unified database is the **single source of truth** for all extracted data:
- OCR results
- Transcriptions
- Translations
- Any future extraction types

Apps can query this data via `list_extractions()` for analytics, chatbot integration, search, etc.
