# Coupling Analysis - Visual Summary

## Current Problem (What's Over-Coupled)

### ❌ BEFORE: Results Disappear

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend UI                              │
│     User sees results, but they disappear on refresh        │
│              (Nothing in database!)                         │
└─────────────────────────────────────────────────────────────┘
                          ▲
                          │ JSON-RPC Response
                          │ (one-time only)
                          │
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server                               │
│              (Request-Response Router)                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ Synchronous call
┌─────────────────────────────────────────────────────────────┐
│                   OCR Agent                                 │
│    ✓ Gets image → ✓ Runs OCR → ✗ Returns result           │
│    ✗ Doesn't store anywhere                                │
│    ✗ No audit trail                                        │
│    ✗ Can't chain to next processor                         │
└─────────────────────────────────────────────────────────────┘
```

### Problems This Causes:
1. **Data Loss**: Refresh page → results gone
2. **No Analytics**: Can't query "how many docs processed"
3. **No Chaining**: OCR results can't flow to Metadata Agent
4. **No Audit**: No history of what was processed when
5. **No ChatGPT-Style Tools**: Can't combine OCR + Metadata for questions
6. **No Retry Logic**: If agent crashes, data is lost forever

---

## ✅ AFTER: Event-Driven with Persistent Storage

```
┌──────────────────────────────────────────────────────────────┐
│                  Frontend UI                                │
│   Polls job_id for status updates                           │
│   Results persist; user sees full history                   │
└────────────────────┬─────────────────────────────────────────┘
                     │ (1) Create job
                     │ (2) Poll for status
                     ▼
┌──────────────────────────────────────────────────────────────┐
│            MongoDB (Central Database)                       │
│                                                             │
│  processing_jobs collection:                               │
│  ┌────────────────────────────────────────────────────┐   │
│  │ document_id: "invoice123"                          │   │
│  │ status: "completed"                                │   │
│  │ stages: {                                          │   │
│  │   ocr: {                                           │   │
│  │     status: "completed",                           │   │
│  │     result: "extracted text here",                │   │
│  │     confidence: 0.92,                             │   │
│  │     timestamp: 2026-03-03T...                      │   │
│  │   },                                              │   │
│  │   metadata: {                                      │   │
│  │     status: "completed",                           │   │
│  │     result: {extracted fields...},                 │   │
│  │     timestamp: 2026-03-03T...                      │   │
│  │   },                                              │   │
│  │   translation: {                                  │   │
│  │     status: "completed",                           │   │
│  │     result: "translated text...",                 │   │
│  │     timestamp: 2026-03-03T...                      │   │
│  │   }                                               │   │
│  │ }                                                  │   │
│  └────────────────────────────────────────────────────┘   │
│                                                             │
│  events collection (immutable audit log):                  │
│  ┌────────────────────────────────────────────────────┐   │
│  │ {doc_id, timestamp, agent, action, result}        │   │
│  │ {doc_id, timestamp, agent, action, result}        │   │
│  │ ...                                               │   │
│  └────────────────────────────────────────────────────┘   │
└────────────────────┬─────────────────────────────────────────┘
                     ▲
           ┌─────────┼─────────┐
           │         │         │
      [Poll]   [Subscribe] [Watch]
           │         │         │
     ┌─────▼──┐ ┌────▼───┐┌────▼─────┐
     │   OCR  │ │Metadata││Translation
     │  Agent │ │ Agent  ││  Agent
     │        │ │        ││
     │ Pulls  │ │ Pulls  ││  Pulls
     │ jobs   │ │ jobs   ││   jobs
     │ from   │ │ from   ││  from
     │ queue  │ │ queue  ││   queue
     │        │ │        ││
     │Process │ │Process ││ Process
     │        │ │        ││
     │ Update │ │ Update ││ Update
     │   DB   │ │   DB   ││   DB
     └────────┘ └────────┘└────────┘
```

---

## Coupling Level Comparison

### BEFORE (Current)

```
Frontend ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ OCR Agent
          (tightly coupled via MCP)
          Waits synchronously
          No data persistence
          No error recovery
          Can't scale

Coupling Score: 6-7/10 (Too Tight)
```

### AFTER (Recommended)

```
Frontend ━━━━━━━┓
                ├─────► Database ◄─────┐
                │                      │
         (async polling)               │ (subscribe)
                                       │
                             ┌─────────▼────────┐
                             │  Event Bus       │
                             │  (Job Queue)     │
                             └─────────┬────────┘
                                       │
                    ┌──────────────────┼──────────────┐
                    │                  │              │
                    ▼                  ▼              ▼
                  OCR              Metadata       Translation
                 Agent              Agent          Agent

Coupling Score: 2-3/10 (Properly Decoupled)
```

---

## Key Benefits Matrix

| Capability | Current | After |
|-----------|---------|-------|
| **Persist Results** | ❌ No | ✅ Yes |
| **Chain Processors** | ❌ No | ✅ Yes |
| **Error Recovery** | ❌ No | ✅ Yes |
| **Audit Trail** | ❌ No | ✅ Yes |
| **ChatGPT Tools** | ❌ No | ✅ Yes |
| **Scalability** | ⚠️ Limited | ✅ Unlimited |
| **Independent Agents** | ⚠️ Somewhat | ✅ Fully |
| **Cost Optimization** | ❌ No | ✅ Yes |
| **Multi-Provider Support** | ⚠️ Hard | ✅ Easy |
| **Data Visibility** | ❌ None | ✅ Complete |

---

## Three Implementation Phases

### Phase 1: Unified Metadata (2-3 hours)
```
Goal: Stop losing data
├─ Create metadata_store.py
├─ Update OCR agent to save results
├─ Add job polling to frontend
└─ Risk: LOW | Value: VERY HIGH
```

### Phase 2: Job Queue (1 week)
```
Goal: Enable multi-stage pipelines
├─ Set up Redis/RabbitMQ
├─ Create job_queue.py
├─ Update agents for async processing
└─ Risk: LOW | Value: HIGH
```

### Phase 3: Provider Abstraction (3 days)
```
Goal: Support multiple OCR providers
├─ Create provider_registry.py
├─ Add UI provider selection
├─ Support Claude, Gemini, etc.
└─ Risk: VERY LOW | Value: HIGH
```

---

## Migration Path

```
Week 1:
  Day 1-2: Phase 1 (Unified Storage)
           ✓ Results now persist
           ✓ Frontend can poll
           ✓ Basic ChatGPT tools possible

Week 2:
  Day 1-5: Phase 2 (Job Queue)
           ✓ OCR → Metadata automatic
           ✓ Metadata → Translation automatic
           ✓ Full pipeline support

Week 3:
  Day 1-3: Phase 3 (Provider Abstraction)
           ✓ Switch providers in UI
           ✓ A/B test different models
           ✓ Cost optimization
```

---

## Backward Compatibility

✅ **Phase 1 is 100% backward compatible**
- Existing sync calls still work
- Frontend can still send/receive via MCP
- Old code continues functioning
- Just add persistence on top

✅ **Phase 2 is opt-in**
- Simple tasks stay sync
- Complex pipelines go async
- No breaking changes

✅ **Phase 3 is opt-in**
- Default to tesseract
- User can select other providers
- No forcing migration

---

## Cost/Benefit Analysis

| Phase | Implementation Hours | Benefit | ROI |
|-------|---------------------|---------|-----|
| Phase 1 | 2-3 | Data persistence + basic querying | 100:1 |
| Phase 2 | 40 | Multi-stage pipelines | 50:1 |
| Phase 3 | 24 | Provider flexibility | 30:1 |
| **Total** | **66-69** | **Full production system** | **⭐⭐⭐⭐⭐** |

---

## Decision Framework

**Start Phase 1 IF:**
- You want OCR results to persist ✅
- You want to build ChatGPT-style tools ✅
- You're tired of fixing timeout issues ✅
- You plan to add Transcription/Translation ✅

**Answer: YES to all → Implement today** ⚡

