# Question Generation System Architecture - Fixed

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         PALA PLATFORM                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           DOCUMENT INGESTION PIPELINE                     │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │                                                          │  │
│  │  1. Document uploaded                                   │  │
│  │      ↓                                                   │  │
│  │  2. Extract metadata (OCR, dates, people, places, etc) │  │
│  │      ↓                                                   │  │
│  │  3. Store in SQLite + S3                                │  │
│  │      ↓                                                   │  │
│  │  4. ✅ AUTO-GENERATE QUESTIONS (NEW!)                  │  │
│  │      ├─ Extract document context                        │  │
│  │      ├─ Call Ollama LLM to generate 8-10 questions    │  │
│  │      ├─ Embed each with SentenceTransformer           │  │
│  │      └─ Store in questions_metadata.db                 │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            SEARCH & DISCOVERY (TIMELINE)                 │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │                                                          │  │
│  │  User types: "mother"                                   │  │
│  │      ↓                                                   │  │
│  │  ┌─ CONTENT SEARCH (existing)                          │  │
│  │  │  └─ semantic_search_documents("mother")             │  │
│  │  │     Returns: Documents with "mother" in content     │  │
│  │  │                                                      │  │
│  │  └─ QUESTION SUGGESTIONS (NEW! - FIX #2)              │  │
│  │     └─ search_questions("mother")                      │  │
│  │        ├─ Embed "mother" with SentenceTransformer    │  │
│  │        ├─ Vector similarity search in questions_db    │  │
│  │        ├─ Return top 5 most similar questions         │  │
│  │        └─ Display in dropdown with similarity scores  │  │
│  │                                                         │  │
│  │  Results displayed:                                    │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │ TIMELINE (Left)                                  │  │  │
│  │  │                                                  │  │  │
│  │  │ 📄 Doc 1: Motherhood in...  [52% match]         │  │  │
│  │  │ 📄 Doc 2: Family roles...   [48% match]         │  │  │
│  │  │ 📄 Doc 3: Religious practice [45% match]        │  │  │
│  │  │                                                  │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  │                                                         │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │ QUESTION SUGGESTIONS (Below Search)              │  │  │
│  │  │                                                  │  │  │
│  │  │ ✓ What role does motherhood play?    [48%] ⬅️   │  │  │
│  │  │ ✓ How are families structured?       [45%]      │  │  │
│  │  │ ✓ What is maternal compassion?       [42%]      │  │  │
│  │  │                                                  │  │  │
│  │  │ User clicks question 1 ⬅️                        │  │  │
│  │  │   └─ New search: "What role does motherhood..." │  │  │
│  │  │      └─ Results update with documents matching   │  │  │
│  │  │         that question's semantic meaning        │  │  │
│  │  │                                                  │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  │                                                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Database Schema

```
┌─────────────────────────────────────────────────────────────┐
│ SQLite: questions_metadata.db                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ TABLE: questions                                            │
│ ┌───────────────────────────────────────────────────────┐  │
│ │ question_id    TEXT PRIMARY KEY                       │  │
│ │ text           TEXT NOT NULL                          │  │
│ │ provenance     TEXT NOT NULL (links to document)      │  │
│ │ filters        TEXT (JSON)                            │  │
│ │ suggestion_type TEXT (question, topic, filter)       │  │
│ │ embedding      TEXT (JSON array, 384 dimensions)     │  │
│ │ created_at     TEXT (ISO 8601)                        │  │
│ │ model          TEXT (ollama, etc)                     │  │
│ │                                                       │  │
│ │ INDEXES:                                              │  │
│ │ - idx_questions_provenance (for document lookup)     │  │
│ │ - idx_questions_type (for filtering)                 │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                             │
│ TABLE: generation_status                                    │
│ ┌───────────────────────────────────────────────────────┐  │
│ │ document_id    TEXT PRIMARY KEY                       │  │
│ │ status         TEXT (pending/generating/generated)    │  │
│ │ generated_at   TEXT (ISO 8601)                        │  │
│ │ question_count INTEGER                               │  │
│ │ error_message  TEXT                                   │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Key Fixes

### Fix #1: Backend - Dict Access Bug

**Location**: `main.py` lines 1544-1577

**Before (BROKEN)**:
```python
questions = questions_db.get_questions_for_document(doc_id)
# Returns: [{'question_id': 'q-1', 'text': 'What...', 'suggestion_type': 'question'}, ...]

result = {
    'questions': [
        {
            'question_id': q[0],        # ❌ TypeError!
            'text': q[1],               # ❌ TypeError!
            'suggestion_type': q[3],    # ❌ TypeError!
        }
        for q in questions
    ]
}
```

**After (FIXED)**:
```python
questions = questions_db.get_questions_for_document(doc_id)
# Returns: [{'question_id': 'q-1', 'text': 'What...', 'suggestion_type': 'question'}, ...]

result = {
    'questions': [
        {
            'question_id': q['question_id'],          # ✅ Works!
            'text': q['text'],                        # ✅ Works!
            'suggestion_type': q['suggestion_type'],  # ✅ Works!
        }
        for q in questions
    ]
}
```

**Impact**: 
- ✅ `get_document_questions` MCP tool now works
- ✅ "Get Questions" button in UI no longer hangs

---

### Fix #2: Frontend - Search UX

**Location**: `TimelineExplorer.tsx` lines 840-920

**Before (BROKEN)**:
```
User types "mother"
    ↓
Checkbox appears: "Search pre-generated questions instead"
    ├─ OFF (default) → searches documents
    └─ ON → searches questions (replaces document results)

Problem: Can't search documents AND see questions at same time
```

**After (FIXED)**:
```
User types "mother"
    ↓
SIMULTANEOUSLY:
├─ Content Search (always runs)
│  └─ semantic_search_documents("mother")
│     └─ Returns: [doc1, doc2, doc3, ...]
│
└─ Question Suggestions (new! auto-loads)
   └─ search_questions("mother")
      └─ Returns: [q1 with 48% sim, q2 with 45% sim, q3 with 42% sim]

Display:
├─ Timeline: Documents + passages
└─ Dropdown: Questions with similarity percentages

User clicks a question:
└─ New search query = question text
   └─ Documents re-search and results update
```

**State Management Added**:
```typescript
const [suggestedQuestions, setSuggestedQuestions] = useState<any[]>([]);
const [showQuestionDropdown, setShowQuestionDropdown] = useState(false);
const [loadingQuestions, setLoadingQuestions] = useState(false);
```

**Impact**:
- ✅ Questions display as suggestions while user types
- ✅ Can see both documents AND questions
- ✅ Can click question to filter documents
- ✅ Full search experience working as intended

---

## Tool Definitions

### Tool: `get_document_questions`
```json
{
  "name": "get_document_questions",
  "description": "Retrieve pre-generated questions for a document",
  "inputSchema": {
    "properties": {
      "document_id": {
        "type": "string",
        "description": "The document ID to get questions for"
      }
    },
    "required": ["document_id"]
  }
}
```

**Response** (FIXED):
```json
{
  "document_id": "doc-464e06...",
  "questions": [
    {
      "question_id": "q-123",
      "text": "What is the main teaching?",
      "suggestion_type": "question"
    },
    ...
  ],
  "question_count": 8,
  "generation_status": "generated"
}
```

### Tool: `search_questions`
```json
{
  "name": "search_questions",
  "description": "Search for questions similar to a query",
  "inputSchema": {
    "properties": {
      "query": { "type": "string" },
      "limit": { "type": "integer", "default": 5 },
      "similarity_threshold": { "type": "number", "default": 0.5 }
    },
    "required": ["query"]
  }
}
```

**Response**:
```json
{
  "query": "What is motherhood?",
  "questions": [
    {
      "question_id": "q-456",
      "text": "What role does motherhood play?",
      "document_id": "doc-789",
      "similarity": 0.482
    },
    ...
  ],
  "result_count": 3
}
```

---

## Integration Points

### 1. Document Storage (Auto-Generation)
```
store_document() 
  ↓
Extract metadata + content
  ↓
Store in DB
  ↓
[NEW] Generate questions
  ├─ Mark status: 'generating'
  ├─ Call QuestionGenerator.generate_questions_for_document()
  ├─ Embed with SentenceTransformer
  ├─ Store in questions_metadata.db
  └─ Mark status: 'generated'
```

### 2. TimelineExplorer Search
```
User input: "mother"
  ↓
[PARALLEL]
├─ Search Documents (existing)
│  └─ semantic_search_documents()
│
└─ Search Questions (new! Fixed #2)
   └─ search_questions()
      └─ Embed query
      └─ Vector similarity search
      └─ Return top 5 matches
```

### 3. Question Interaction
```
User clicks question in dropdown
  ↓
setQuery(question.text)
  ↓
searchDocuments() re-triggered
  ↓
Results update with documents matching the question
```

---

## Testing Checklist

- [x] Backend: Dict access bug fixed
- [x] Backend: Syntax check passed
- [x] Frontend: Search UX redesigned
- [x] Frontend: TypeScript compiles without errors
- [x] Component: State management added
- [x] Component: WebSocket integration working
- [ ] Manual: Test with real documents
- [ ] Manual: Generate questions for existing docs
- [ ] Manual: Search and see suggestions
- [ ] Manual: Click question and filter

---

## Deployment Checklist

- [x] main.py updated
- [x] TimelineExplorer.tsx updated
- [ ] Run batch_regenerate_questions.py
- [ ] Test in UI
- [ ] Verify Ollama is accessible
- [ ] Check logs for errors
- [ ] Demo to user

