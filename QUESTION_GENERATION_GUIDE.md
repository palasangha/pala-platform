# Question Generation System - Complete Guide

## Overview

The Pala Platform now includes an **offline question pre-generation** system that automatically generates 8-10 contextual questions for every document at ingestion time. Questions are embedded using sentence-transformers and stored in SQLite for vector similarity search.

## Features

✅ **Auto-Generation at Ingestion**: Questions generated automatically when documents are stored via `process_and_store_document`  
✅ **Vector Similarity Search**: Find semantically similar pre-generated questions for any query  
✅ **Status Tracking**: Monitor question generation status per document (pending/generating/generated/failed)  
✅ **Regeneration Support**: Manually regenerate questions after metadata updates  
✅ **Batch Processing**: Generate questions for all existing documents with checkpoint/resume capability  
✅ **UI Integration**: View, retrieve, and regenerate questions directly from ContentBrowser  

## Architecture

### Components

```
question_generator.py
  └─ QuestionGenerator class
     ├─ _extract_document_context()    → Extract metadata/content
     ├─ _build_generation_prompt()     → Create LLM prompt
     ├─ _call_ollama()                 → Call local Ollama instance
     └─ generate_questions_for_document() → Main async entry point

questions_db.py
  └─ QuestionsDB class
     ├─ store_question()               → Single question storage
     ├─ store_questions_batch()        → Bulk insert transaction
     ├─ get_questions_for_document()   → Retrieve by doc_id
     ├─ search_questions_by_embedding() → Vector similarity search
     ├─ mark_generation_status()       → Track generation state
     └─ get_generation_status()        → Retrieve status

batch_regenerate_questions.py
  └─ Batch job script
     ├─ Resume from checkpoint         → Fault tolerance
     ├─ Rate limiting                  → Prevent Ollama overload
     └─ Statistics collection          → Progress tracking
```

### Flow

1. **Document Ingestion**
   ```
   process_and_store_document
   └─ store_document (storage-agent)
      ├─ Store file to S3 + SQLite
      └─ [ASYNC] Generate questions
         ├─ QuestionGenerator.generate_questions_for_document()
         ├─ Call Ollama with document context
         ├─ Embed each question with sentence-transformers
         └─ Store in questions_metadata.db
   ```

2. **Question Retrieval (UI)**
   ```
   ContentBrowser (view document)
   └─ [Button] Get Questions
      ├─ Call get_document_questions tool
      ├─ Query questions_db
      └─ Display question list
   ```

3. **Question Search (API)**
   ```
   search_questions("user query")
   ├─ Embed query with sentence-transformers
   ├─ Calculate cosine similarity vs all questions
   ├─ Return top-k results by similarity
   └─ Include source document_id + question text
   ```

4. **Batch Regeneration**
   ```
   batch_regenerate_questions.py
   ├─ List all documents
   ├─ For each doc:
   │  ├─ Call generate_questions_for_document()
   │  ├─ Save checkpoint after each success
   │  └─ Track error if fails
   └─ Support --resume to pick up where you left off
   ```

## Database Schema

**questions_metadata.db**

```sql
CREATE TABLE questions (
  question_id TEXT PRIMARY KEY,
  text TEXT NOT NULL,
  provenance TEXT,                    -- source document_id
  filters TEXT,                       -- JSON: tags, type, language, location, etc
  suggestion_type TEXT,               -- 'question' | 'topic' | 'filter' | 'expand'
  embedding TEXT,                     -- JSON array of 384 floats
  created_at TEXT,
  updated_at TEXT,
  model TEXT
);

CREATE TABLE generation_status (
  document_id TEXT PRIMARY KEY,
  status TEXT,                        -- 'pending' | 'generating' | 'generated' | 'failed'
  generated_at TEXT,
  question_count INTEGER,
  error_message TEXT
);
```

## Quick Start

### 1. Verify Prerequisites

```bash
# Ollama running locally
curl http://localhost:11434/api/tags

# Python environment with requirements
python3 -c "from sentence_transformers import SentenceTransformer; print('✓ sentence-transformers installed')"
```

### 2. Upload a Document (Auto-generates Questions)

**Via Dashboard:**
1. Open PalaWebDashboard → Sample Agent
2. Select "process_and_store_document" tool
3. Upload a PDF/text file
4. Watch console logs for `[QUESTION-GEN] ✅ Generated X questions`

**Via API (direct):**
```bash
curl -X POST http://localhost:8000/api/documents \
  -H "Content-Type: application/json" \
  -d '{
    "original_file": "base64-encoded-content",
    "original_file_name": "document.pdf",
    "file_format": "pdf",
    "document_type": "ocr",
    "created_by": "test-user"
  }'
```

### 3. Retrieve Questions for a Document

**Via Dashboard:**
1. Open Storage Agent → "get_document_questions" tool
2. Enter document_id
3. View returned questions with IDs and types

**Via JSON-RPC:**
```json
{
  "method": "invoke",
  "params": {
    "name": "get_document_questions",
    "arguments": {
      "document_id": "doc-12345678"
    }
  }
}
```

### 4. Search for Similar Questions

**Via Dashboard:**
1. Open Storage Agent → "search_questions" tool
2. Enter query: "Buddhist meditation practices"
3. See similar pre-generated questions ranked by cosine similarity

**Via API:**
```json
{
  "method": "invoke",
  "params": {
    "name": "search_questions",
    "arguments": {
      "query": "meditation techniques",
      "limit": 5,
      "similarity_threshold": 0.5
    }
  }
}
```

### 5. Regenerate Questions After Metadata Update

**Via ContentBrowser:**
1. Open document details modal
2. Edit metadata fields
3. Click "Regenerate Questions" button
4. Questions re-generated with new context

**Via API:**
```json
{
  "method": "invoke",
  "params": {
    "name": "regenerate_document_questions",
    "arguments": {
      "document_id": "doc-12345678"
    }
  }
}
```

### 6. Batch Generate Questions for Existing Documents

```bash
# Start batch regeneration
cd packages/PalaAgents/storage-agent/
python3 batch_regenerate_questions.py --limit 100 --delay 2.0

# Resume from checkpoint
python3 batch_regenerate_questions.py --resume

# Dry run (see what would be processed)
python3 batch_regenerate_questions.py --dry-run --limit 10

# Skip documents that already have questions
python3 batch_regenerate_questions.py --skip-existing
```

**Options:**
- `--limit N`: Process max N documents
- `--resume`: Resume from checkpoint
- `--skip-existing`: Don't regenerate for docs with existing questions
- `--dry-run`: Show what would be processed without making changes
- `--delay SECONDS`: Pause between documents (default: 2.0)

**Progress Tracking:**
- Checkpoint saved to: `packages/PalaAgents/storage-agent/data/batch_regeneration_checkpoint.json`
- Contains: processed_count, processed_ids, stats
- Auto-saves every 10 documents

## Configuration

### Environment Variables

```bash
# Ollama
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=mistral

# Disable Ollama (optional)
export OLLAMA_ENABLED=false

# Storage
export STORAGE_PROVIDER=sqlite  # Only sqlite supported currently
```

### Embedding Model

Uses **sentence-transformers** with model `all-MiniLM-L6-v2`:
- 384-dimensional embeddings
- Fast inference, good quality
- Installed automatically on first use

### Vector Search Thresholds

Default similarity threshold: **0.5**  
Recommended thresholds:
- **0.7+**: Very similar questions (high precision)
- **0.5-0.7**: Moderately similar (balanced)
- **0.3-0.5**: Loosely related (high recall)
- **0.0-0.3**: Exploratory search

## Monitoring & Logging

### Log Levels

Storage-agent logs all question operations with `[QUESTION-GEN]` prefix:

```
[QUESTION-GEN] Initialized QuestionGenerator with Ollama provider
[QUESTION-GEN] Generating questions for document test-doc-001
[QUESTION-GEN] Extracted context for doc test-doc-001: 344 chars
[QUESTION-GEN] Calling Ollama for doc test-doc-001
[QUESTION-GEN] Generated 8 questions for doc test-doc-001
[QUESTION-GEN] ✅ Generated and stored 8 questions for test-doc-001
```

### Check Generation Status

```python
from questions_db import QuestionsDB

db = QuestionsDB('data/questions_metadata.db')
status = db.get_generation_status('doc-12345678')
# Returns: ('generated', timestamp, 8, error_msg)
```

### Database Inspection

```bash
sqlite3 packages/PalaAgents/storage-agent/data/questions_metadata.db

# Count questions by document
.mode column
SELECT provenance, COUNT(*) as count FROM questions GROUP BY provenance;

# View questions for a document
SELECT text, suggestion_type FROM questions WHERE provenance = 'doc-xyz' LIMIT 5;

# Check generation status
SELECT * FROM generation_status WHERE status = 'failed';
```

## Testing

Run comprehensive unit tests:

```bash
cd packages/PalaAgents/storage-agent/
python3 test_question_generation.py
```

**Test Coverage:**
- ✅ Question generation from documents
- ✅ Storage and retrieval
- ✅ Batch storage operations
- ✅ Generation status tracking
- ✅ Vector similarity search
- ✅ Question regeneration

All tests should show `6 | Passed: 6 | Failed: 0`

## Troubleshooting

### Questions Not Generated

**Check 1:** Verify Ollama is running
```bash
curl http://localhost:11434/api/tags
# Should return: { "models": [...] }
```

**Check 2:** Check storage-agent logs for errors
```bash
tail -f logs/storage-agent.log | grep QUESTION-GEN
```

**Check 3:** Verify document has sufficient metadata
- Questions require at least title or summary
- Empty/minimal documents may generate no questions

### Slow Question Generation

Questions are generated **asynchronously** after document storage completes. Normal time:
- 1-2 seconds per document (network + Ollama)
- Adjust `--delay` in batch script if needed

### Embedding Model Not Loading

```bash
# Install sentence-transformers
pip install sentence-transformers

# Test import
python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
# First run downloads model (~80MB)
```

### Vector Search Returns No Results

Adjust similarity threshold:
```json
{
  "query": "your search",
  "similarity_threshold": 0.3
}
```

Lower threshold → more results (but less relevant)

## Architecture Integration Points

### Storage Agent (`main.py`)

```python
# Initialization
ollama_provider = OllamaMetadataProvider(...)  # Line ~130
questions_db = QuestionsDB(...)               # Line ~150

# In store_document
if ollama_provider and questions_db:
    gen = QuestionGenerator(ollama_provider)
    questions = await gen.generate_questions_for_document(...)
    questions_db.store_questions_batch(questions)
```

### New Tools Registered

1. **get_document_questions** - Retrieve pre-generated questions
2. **search_questions** - Vector similarity search
3. **regenerate_document_questions** - Refresh after metadata changes

### UI Integration (`ContentBrowser.tsx`)

- "Get Questions" button → calls get_document_questions
- "Regenerate Questions" button → calls regenerate_document_questions
- Results displayed in document detail modal

## Performance Notes

### Question Generation
- 1 document: ~2-3 seconds (Ollama call + embedding + storage)
- 100 documents: ~3-5 minutes (with default --delay=2.0)
- Batch job saves checkpoint every 10 documents for recovery

### Vector Search
- Query embedding: ~50ms
- Similarity calculation: O(n) where n = total questions
- 1000 questions: ~100-200ms
- 10000 questions: ~1-2 seconds

### Storage
- Per-document questions: ~8-10 rows
- Embedding size: ~384 floats = ~3KB per question
- 100 documents: ~3MB total (question + embedding)

## Future Enhancements

Potential improvements:
- [ ] Multi-language question generation
- [ ] Custom question types (follow-up, clarification, etc.)
- [ ] Question quality scoring
- [ ] Integration with retrieval augmented generation (RAG)
- [ ] Vector DB backend (Pinecone, Milvus) for scaling
- [ ] Real-time question streaming UI
- [ ] A/B testing different question generation prompts

## Support & Debugging

For issues or questions:

1. Check logs: `tail -f logs/storage-agent.log`
2. Run tests: `python3 test_question_generation.py`
3. Inspect DB: `sqlite3 data/questions_metadata.db`
4. Check Ollama: `curl http://localhost:11434/api/tags`
