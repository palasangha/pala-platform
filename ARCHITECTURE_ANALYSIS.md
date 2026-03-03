# Pala Platform - Architecture Analysis: Coupling & Decoupling Strategies

**Date:** March 2026  
**Focus:** Assess current coupling levels and explore alternatives for OCR, Transcription, Translation, and other processors

---

## Table of Contents

1. [Current Architecture Overview](#current-architecture-overview)
2. [Coupling Assessment](#coupling-assessment)
3. [Where You ARE Over-Coupled](#where-you-are-over-coupled)
4. [Architecture Options & Recommendations](#architecture-options--recommendations)
5. [Recommended Path Forward](#recommended-path-forward)

---

## Current Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                         │
│                    @ localhost:3001                             │
│  Dashboard → FileReader (base64) → WebSocket → MCP Client      │
└────────────────────────┬────────────────────────────────────────┘
                         │ JSON-RPC 2.0 WebSocket
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  MCP Server (TypeScript)                        │
│                    @ localhost:3000                             │
│  • Tool Registry        • Request Router                        │
│  • Agent Manager        • Response Handler                      │
│  • Auth & Logging       • 30min timeout for long ops            │
└────────────────────────┬────────────────────────────────────────┘
                         │ JSON-RPC 2.0 WebSocket
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
    ┌─────────────┐┌──────────┐┌──────────────┐
    │ OCR Agent   ││Metadata  ││Storage Agent │
    │(Python)    ││Agent     ││(Python)      │
    │Tesseract   ││(Python)  ││SQLite DB     │
    │Ollama      ││Claude    ││              │
    │LM Studio   ││API       ││              │
    └─────────────┘└──────────┘└──────────────┘
```

### Data Flow: Current State

```
User uploads JPEG
  ↓
[Frontend] Converts to base64
  ↓
[MCP Server] Routes to ocr-agent
  ↓
[OCR Agent] Receives base64 → Saves temp file → Calls Ollama
  ↓
[Ollama] Returns extracted text
  ↓
[OCR Agent] Returns result to MCP
  ↓
[Frontend] Displays text to user
  ✗ NO DATABASE STORAGE YET
```

---

## Coupling Assessment

### Current Coupling Levels (Scale: 1=Loose, 10=Tight)

| Component | Coupling | Issues | Severity |
|-----------|----------|--------|----------|
| **Frontend → MCP** | 4/10 | WebSocket protocol is clean | ✅ Good |
| **MCP → Agents** | 5/10 | JSON-RPC is language-agnostic | ✅ Acceptable |
| **OCR Agent → Providers** | 6/10 | Hard-coded provider imports | ⚠️ Medium |
| **Agents → Metadata Storage** | 8/10 | Each agent writes own metadata; no unified schema | ❌ **PROBLEM** |
| **OCR → DB** | 9/10 | No database persistence; results live in memory | ❌ **CRITICAL** |
| **Multiple Agents → Shared DB** | N/A | **MISSING COMPONENT** | ❌ **BLOCKER** |
| **Agent → External APIs** | 7/10 | Ollama/Claude hardcoded; no provider abstraction | ⚠️ Medium |

### Where You ARE Over-Coupled

#### 1. **Each Agent is Isolated with No Unified Metadata Store** (CRITICAL)

**Current Problem:**
```python
# ocr-agent/main.py
result = {
    "text": extracted_text,
    "confidence": 0.92,
    "metadata": {...}
}
# ❌ Returns to MCP → returns to frontend
# ❌ Nothing persists to database
# ❌ Each agent produces its own metadata format
# ❌ No way to query across agents (e.g., "show me all documents with low OCR confidence")
```

**Why This Sucks:**
- OCR results disappear after browser closes
- Can't do ChatGPT-style analysis across all extracted data
- Metadata from transcription/translation agents won't connect to OCR metadata
- No audit trail, no versioning, no deduplication

#### 2. **No Message Queue Between Agents** (HIGH COUPLING)

**Current Problem:**
```typescript
// MCP Server synchronously routes: UI → MCP → Agent → Provider → Result
// ❌ All processing is request-response synchronous
// ❌ No way to chain OCR → Metadata Extraction → Translation
// ❌ If agent crashes, data is lost
// ❌ No retry logic, no job tracking beyond single agent
```

**Real-World Scenario:**
```
User uploads document
  → OCR extracts text (5 minutes) ✓
  → Should auto-trigger metadata extraction
  → Should auto-trigger translation
  → But there's NO QUEUE connecting them
  → If MCP crashes mid-pipeline, everything is lost
```

#### 3. **Agent Result Formats Are Inconsistent** (MEDIUM COUPLING)

**Current Problem:**
```python
# ocr-agent returns:
{
    "text": "extracted text",
    "confidence": 0.92,
    "metadata": {"provider": "ollama", ...}
}

# metadata-agent would return something different:
{
    "extracted_fields": {...},
    "confidence": {...},
    "metadata": {...}
}

# translation-agent would have its own format
# ❌ Frontend can't uniformly handle results
# ❌ Can't store uniformly in database
# ❌ Can't chain agents together
```

#### 4. **Direct Provider Dependencies** (MEDIUM COUPLING)

**Current Problem:**
```python
# ocr-agent/providers/ollama_provider.py
# ❌ Hardcoded to specific Ollama model
# ❌ If you want to swap Ollama → LM Studio, need code changes
# ❌ No provider abstraction layer for extensibility

class OllamaProvider:
    def __init__(self):
        self.host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.model = 'minicpm-v'  # ← Hard-coded
```

---

## Architecture Options & Recommendations

### Option A: Event-Driven Architecture (RECOMMENDED) 🎯

**Philosophy:** Decouple via events and persistent state

```
┌──────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│              [Upload JPEG] → [MCP Client]                   │
└─────────────────────────┬──────────────────────────────────┘
                          │ Create Job (document_id, status)
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                     Central Database                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ documents collection:                               │   │
│  │ {                                                    │   │
│  │   _id: UUID,                                         │   │
│  │   filename: "invoice.pdf",                           │   │
│  │   status: "uploaded" → "ocr_processing" → etc        │   │
│  │   raw_content: base64,                               │   │
│  │   stages: {                                          │   │
│  │     ocr: {status, result, error, timestamp},        │   │
│  │     metadata: {status, result, error, timestamp},   │   │
│  │     translation: {status, result, error, timestamp},│   │
│  │     custom: {...}                                   │   │
│  │   }                                                  │   │
│  │ }                                                    │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ events collection (immutable log):                   │   │
│  │ {document_id, agent, stage, status, result, error}  │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
                          ▲
           ┌──────────────┼──────────────┐
           │              │              │
      [Poll/Query]    [Subscribe]   [Webhook]
           │              │              │
     ┌─────▼───┐     ┌────▼─────┐  ┌────▼─────┐
     │   OCR   │     │Metadata  │  │Translation
     │  Agent  │     │ Extractor│  │ Agent
     │(watches │     │(watches  │  │(watches
     │ jobs w/ │     │ jobs w/  │  │ jobs w/
     │status:  │     │ status:  │  │ status:
     │pending) │     │ ocr_done)│  │ metadata_
     │         │     │          │  │ done)
     └─────┬───┘     └────┬─────┘  └────┬─────┘
           │              │              │
           └──────────────┼──────────────┘
                          │
                   [Update document]
                   [Add to events log]
                   [Trigger next stage]
```

**Advantages:**
- ✅ Agents are completely independent
- ✅ Each agent only cares about: fetch job, process, update DB, trigger next
- ✅ Easy to add new agents (transcription, translation, etc.)
- ✅ Natural error handling and retries
- ✅ Full audit trail in events log
- ✅ Can pause/resume pipelines
- ✅ Enables ChatGPT-style tool calling: "Use OCR results + Metadata to answer user question"
- ✅ Frontend polls DB, not waiting on MCP response

**Disadvantages:**
- More complex; requires job/event infrastructure
- Slightly higher latency (but acceptable for most document processing)

---

### Option B: Request-Response with Central Service Layer (GOOD)

**Philosophy:** Keep synchronous but add unified result storage

```
Frontend
  ↓
MCP Server
  ↓
┌─────────────────────────────┐
│  Processing Orchestrator    │
│  (NEW service)              │
│  - Handles job creation     │
│  - Stores results           │
│  - Manages persistence      │
└────────────┬────────────────┘
             │
        ┌────┴────────────────┐
        ▼                     ▼
    OCR Agent          Metadata Agent
  (unchanged)          (unchanged)
    - Process            - Process
    - Return             - Return
```

**Advantages:**
- ✅ Less architectural change
- ✅ Results go through unified storage layer
- ✅ Still relatively simple

**Disadvantages:**
- ❌ No natural pipeline chaining
- ❌ Still synchronous (MCP timeout issues will persist)
- ❌ Can't handle long-running chains (OCR → Metadata → Translation)
- ❌ Frontend still blocked waiting for response

---

### Option C: Hybrid: Sync for Simple, Async for Complex (ACCEPTABLE)

**Philosophy:** Use sync for single-agent tasks, async for multi-stage pipelines

```
Single task (OCR only):
  Frontend → MCP → OCR Agent → Result (sync, fast)

Complex pipeline (OCR + Metadata + Translation):
  Frontend → MCP → Job Created → Database
  (Frontend polls for status)
  
  Backend:
    Stage 1: OCR Agent processes, updates DB
    Stage 2: Metadata Agent processes, updates DB
    Stage 3: Translation Agent processes, updates DB
    
  Frontend checks status until done
```

---

## Recommended Path Forward

### Phase 1: Unified Metadata Layer (Immediate) ⚡

**Goal:** Stop losing OCR results; create foundation for all agents

```python
# new file: packages/shared/metadata_store.py

class MetadataStore:
    """
    Unified storage for all processor results
    
    Every agent writes to same schema:
    - content_id (unique identifier)
    - processor_type (ocr, transcription, translation, metadata)
    - stage (pending, processing, completed, failed)
    - input (what was processed)
    - output (result)
    - metadata (confidence, model_used, cost, duration)
    - error (if failed)
    - created_at, updated_at
    """
    
    def create_job(self, content_id: str, processor_type: str, input_data: dict):
        """Create new processing job"""
        return {
            "job_id": uuid(),
            "content_id": content_id,
            "processor_type": processor_type,
            "status": "pending",
            "stages": {}
        }
    
    def update_job(self, job_id: str, stage: str, status: str, result: dict):
        """Update job with stage result"""
        # Store in DB
        
    def get_job(self, job_id: str):
        """Retrieve job with all stages"""
        return {...}
    
    def list_by_content(self, content_id: str):
        """Get all processing results for a document"""
        return [ocr_result, metadata_result, translation_result, ...]
```

**Changes to OCR Agent:**
```python
# Instead of returning result directly
result = ocr_provider.extract_text(image_path)

# Now also store it
metadata_store.update_job(
    job_id=params['job_id'],
    stage='ocr',
    status='completed',
    result=result
)

# Frontend polls job_id to check completion
```

**Implementation:**
1. Create `packages/shared/metadata_store.py` (Python utils + DB schemas)
2. Update `ocr-agent` to store results
3. Add `get_job` tool to MCP for polling
4. Update Frontend to poll instead of waiting

**Database Schema (MongoDB):**
```javascript
db.processing_jobs.insertOne({
  _id: ObjectId,
  content_id: UUID,          // The document being processed
  processor_type: "ocr",     // What processor is handling this
  status: "completed",       // pending, processing, completed, failed
  input: {
    filename: "invoice.pdf",
    file_size: 128000,
    format: "pdf"
  },
  output: {
    text: "extracted text...",
    confidence: 0.92
  },
  metadata: {
    model: "minicpm-v",
    provider: "ollama",
    duration_seconds: 120,
    cost_usd: 0,
    timestamp: ISODate()
  },
  error: null,
  created_at: ISODate(),
  updated_at: ISODate()
})
```

**Time to Implement:** 2-3 hours

---

### Phase 2: Message Queue for Pipeline Chaining (Next Week) 📬

**Goal:** Enable multi-stage workflows (OCR → Metadata → Translation)

```python
# new file: packages/shared/job_queue.py

class JobQueue:
    """
    FIFO queue for multi-stage processing
    
    After OCR completes, automatically queue Metadata job
    After Metadata completes, automatically queue Translation job
    """
    
    def enqueue(self, job_config: dict):
        """Add job to queue"""
        # Store in Redis or MongoDB
    
    def dequeue(self, processor_type: str):
        """Agents poll this to get next job"""
        # Block until job available
```

**Example Workflow:**
```
1. User uploads document
2. System creates: processing_job {content_id, status: "pending"}
3. Queue: [ocr_job, metadata_job, translation_job]
4. OCR Agent polls, gets ocr_job
   → Processes
   → Updates processing_job.stages.ocr = {status: "completed", result: {...}}
   → Signals metadata_job to start
5. Metadata Agent polls, gets metadata_job
   → Reads OCR results from processing_job
   → Processes
   → Updates processing_job.stages.metadata = {status: "completed", result: {...}}
   → Signals translation_job to start
6. Translation Agent polls, gets translation_job
   → Reads OCR results + Metadata
   → Processes
   → Updates processing_job.stages.translation = {status: "completed", result: {...}}
7. Frontend polls job_id, sees all stages complete
   → Displays unified result
```

**Time to Implement:** 1 week (including Redis/queue setup)

---

### Phase 3: Provider Abstraction (Within 2 Weeks) 🔌

**Goal:** Make OCR provider swappable without code changes

```python
# new file: packages/agents/ocr-agent/providers/registry.py

class ProviderRegistry:
    """
    Provider factory with configuration-based selection
    
    Supports Tesseract, Ollama, LM Studio, Claude, Gemini
    Selected via env var or API parameter
    """
    
    def __init__(self):
        self.providers = {
            'tesseract': TesseractProvider,
            'ollama': OllamaProvider,
            'lmstudio': LMStudioProvider,
            'claude': ClaudeProvider,
            'gemini': GeminiProvider,
        }
    
    def get_provider(self, provider_name: str):
        """Instantiate provider"""
        Provider = self.providers.get(provider_name)
        if not Provider:
            raise ValueError(f"Unknown provider: {provider_name}")
        return Provider()
```

**Changes to OCR Agent:**
```python
# Instead of hardcoding Ollama
provider_name = params.get('provider', 'tesseract')
provider = ProviderRegistry().get_provider(provider_name)
result = await provider.extract_text(image_path, language)
```

**Benefits:**
- ✅ User selects provider in UI
- ✅ Easy to add new providers
- ✅ Can A/B test providers (OCR with Tesseract vs Ollama vs Claude)
- ✅ Cost optimization (use cheaper provider for high-confidence docs)

**Time to Implement:** 3 days

---

## Detailed Comparison: Which Path Should You Take?

| Aspect | Option A: Event-Driven | Option B: Sync + Storage | Option C: Hybrid |
|--------|------------------------|--------------------------|-----------------|
| **Complexity** | High | Medium | Medium |
| **Time to Implement** | 2-3 weeks | 1 week | 1.5 weeks |
| **Supports Multi-Stage Pipelines** | ✅ Native | ❌ Requires hacks | ✅ Yes |
| **Fault Tolerance** | ✅ Excellent | ⚠️ Okay | ✅ Good |
| **Data Persistence** | ✅ Full history | ✅ Yes | ✅ Yes |
| **ChatGPT-Style Tools** | ✅ Perfect | ⚠️ Possible | ✅ Yes |
| **Scalability** | ✅ Unlimited | ⚠️ MCP bottleneck | ✅ Good |
| **Production Ready** | ✅ 4+ weeks | ✅ 2 weeks | ✅ 3 weeks |

---

## My Recommendation: Hybrid with Roadmap to Event-Driven

### Why This Path?

1. **Immediate wins** (Phase 1: This week)
   - Stop losing data
   - Enable basic job polling
   - Unblock frontend development

2. **Quick scaling** (Phase 2: Next week)
   - Add message queue
   - Enable pipeline chaining
   - No more architectural rewrites

3. **Long-term flexibility** (Phase 3: Week 3)
   - Provider abstraction
   - Multi-provider A/B testing
   - Cost optimization

### Implementation Priority

**THIS WEEK:**
```
1. Create packages/shared/metadata_store.py
2. Update ocr-agent to call metadata_store.update_job()
3. Add get_job and list_jobs tools to MCP
4. Update Frontend to poll instead of wait
5. Test OCR → DB → Poll flow
```

**NEXT WEEK:**
```
1. Add Redis/RabbitMQ for job queue
2. Create JobQueue class
3. Update all agents to support job queuing
4. Add trigger logic (OCR done → start Metadata)
```

**WEEK 3:**
```
1. Create ProviderRegistry
2. Add provider selection to UI
3. Implement multi-provider support
4. Add cost tracking per provider
```

---

## Code Structure After Changes

```
packages/
├── shared/
│   ├── metadata_store.py      ← NEW: Unified result storage
│   ├── job_queue.py           ← NEW: Multi-stage coordination
│   ├── provider_registry.py   ← NEW: Provider abstraction
│   └── models/
│       ├── processing_job.py  ← NEW: Unified schema
│       └── ...
├── agents/
│   ├── ocr-agent/
│   │   ├── main.py            ← Updated: Use metadata_store
│   │   └── providers/
│   │       ├── registry.py    ← NEW: Provider factory
│   │       ├── base.py        ← Common interface
│   │       └── ...
│   ├── transcription-agent/   ← NEW: Uses metadata_store
│   ├── translation-agent/     ← NEW: Uses metadata_store
│   └── metadata-agent/        ← Updated: Use metadata_store
├── mcp-server/
│   └── tools/
│       ├── ocr.ts
│       ├── get_job.ts         ← NEW: Job status polling
│       └── ...
└── ...

apps/
└── web/
    └── components/
        └── Dashboard.tsx      ← Updated: Poll instead of wait
```

---

## Decoupling Checklist

- [ ] **Phase 1: Unified Storage**
  - [ ] Create `metadata_store.py` with database schema
  - [ ] Update OCR Agent to persist results
  - [ ] Add `get_job` tool to MCP
  - [ ] Update Frontend to poll
  - [ ] Test end-to-end flow

- [ ] **Phase 2: Job Queue**
  - [ ] Set up Redis/RabbitMQ
  - [ ] Create `job_queue.py`
  - [ ] Update all agents for queue-based execution
  - [ ] Add stage triggers
  - [ ] Test multi-stage pipeline

- [ ] **Phase 3: Provider Abstraction**
  - [ ] Create `provider_registry.py`
  - [ ] Refactor OCR providers to use registry
  - [ ] Add provider selection to UI
  - [ ] Test multi-provider switching

---

## FAQ

**Q: Will this break existing frontend?**
A: No. Phase 1 is backward compatible. Frontend can still do sync calls for simple OCR, just with better error handling and data persistence.

**Q: What about concurrent requests?**
A: Event-driven architecture handles this naturally. Each job_id is independent. No conflicts.

**Q: Can I mix sync and async?**
A: Yes! Phase 3 (Hybrid) does exactly this. Fast simple tasks stay sync, complex pipelines go async.

**Q: What if an agent crashes mid-pipeline?**
A: Job queue handles retries automatically. No data loss. Excellent for production.

**Q: How does this enable ChatGPT-style tools?**
A: After Pipeline completion, all results are in database. System can query: "Use OCR results + Metadata extraction + Translation to answer user question." Then synthesize with Claude.

---

## Next Steps

1. **Review** this analysis with your team
2. **Decide** which phase to start with
3. **I recommend:** Start Phase 1 TODAY (2-3 hours work)
4. **Then schedule:** Phase 2 and Phase 3 for next 2 weeks

Would you like me to start implementing Phase 1 (Unified Metadata Storage)?

