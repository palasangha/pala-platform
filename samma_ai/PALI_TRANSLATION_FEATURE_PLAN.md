# Samma AI — Pali Translation with Deepseek Fallback

**Feature:** Automatic Pali-to-English translation fallback using Ollama Deepseek model
**Status:** Design Plan (No changes made)
**Priority:** Medium (improves user experience for rare/untranslated passages)
**Complexity:** Medium (requires integration with existing search + response pipeline)

---

## 1. Current State Analysis

### 1.1 How Translations Currently Work

**Source:** Tipitaka database (`tipitaka_ultimate.db`)

```
Database Structure:
├── paragraphs table (73,765 rows total)
│   ├── id (PRIMARY KEY)
│   ├── pali_text (Pali language)
│   ├── english_text (English translation — MAY BE NULL)
│   ├── reference (e.g., "DN 1.1")
│   ├── pitaka_name (Digha, Majjhima, Samyutta, etc.)
│   ├── nikaya_name
│   ├── book_name
│   ├── sutta_name
│   ├── paragraph_number
│   ├── xml_source_file
│   ├── text_layer ('mula' for canonical, 'attha', 'tika', etc.)
│   └── created_at
```

**Coverage:**
- Total canonical passages (text_layer='mula'): 22,213
- Estimated with English translation: ~99% (219,000+ pairs)
- **Gap:** ~1% of passages have `english_text = NULL` or empty

**Current Pipeline:**

```
User Message
    ↓
[Step 1] TipitakaService.search_relevant_passages()
    ├─→ Vector search via Qdrant
    ├─→ FTS5 search on Pali text
    └─→ Merge results (hybrid)
    ↓
[Step 2] Passages returned with:
    ├─ pali_text ✅
    ├─ english_text ⚠️ (may be NULL)
    ├─ reference ✅
    └─ xml_source ✅
    ↓
[Step 3] ModelRouterService.generate_dhamma_response()
    └─→ LLM processes passages with existing translations
    ↓
[Step 4] ResponseFormatter.format_dhamma_response()
    └─→ Frontend displays formatted response
```

### 1.2 Where Translations Are Missing

**Scenarios:**
1. **Atthakatha (commentary) layer** — Extra interpretive texts
2. **Tika (subcommentary) layer** — Expanded explanations
3. **Newly added passages** — Not yet translated
4. **Edge cases** — Variant readings, abbreviations
5. **User adds custom passages** — Future feature

**Impact on UX:**
- If `english_text` is NULL → Frontend displays Pali only
- User cannot understand the meaning
- Response quality degrades

---

## 2. Proposed Solution: Deepseek Translation Fallback

### 2.1 Architecture Overview

```
User Message
    ↓
[Step 1] TipitakaService.search_relevant_passages()
    ├─→ Fetch passages (may have NULL english_text)
    ↓
[NEW] TranslationService.enrich_passages_with_translations()
    ├─→ Check each passage:
    │   ├─ If english_text exists → SKIP
    │   ├─ If english_text NULL → TRANSLATE via Deepseek
    │   └─ Cache result for future use
    └─→ Return enriched passages
    ↓
[Step 3] ModelRouterService.generate_dhamma_response()
    ├─→ All passages now have english_text
    └─→ LLM processes complete information
    ↓
[Step 4] ResponseFormatter.format_dhamma_response()
    └─→ Full response with translations
```

### 2.2 New Service: TranslationService

**Purpose:** Translate Pali passages using Deepseek when DB translations unavailable

**Dependencies:**
- `requests` library (HTTP calls to Ollama)
- `flask` (access to config)
- SQLite (caching layer)

**Key Methods:**
```python
class TranslationService:
    def translate_pali_passage(
        self,
        pali_text: str,
        reference: str = None
    ) -> str:
        """Translate Pali passage using Deepseek model."""
        # 1. Check cache
        # 2. If cached → return
        # 3. If not → call Deepseek
        # 4. Cache result
        # 5. Return translation

    def enrich_passages_with_translations(
        self,
        passages: List[Dict]
    ) -> List[Dict]:
        """Ensure all passages have english_text."""
        # For each passage:
        # - If english_text exists → skip
        # - If NULL → translate → update passage dict
        # Return enriched passages

    def batch_translate(
        self,
        pali_texts: List[str]
    ) -> Dict[str, str]:
        """Translate multiple passages in parallel."""
```

---

## 3. Detailed Implementation Plan

### Phase A: Infrastructure Setup (1-2 hours)

#### Task A.1: Create TranslationService

**File:** `backend/app/services/translation_service.py`

**Purpose:** Manage Pali-to-English translation via Deepseek

**Key features:**
- Call Ollama Deepseek API endpoint
- Cache translations in SQLite
- Fallback to original Pali if translation fails
- Configurable model and endpoint

**Configuration (settings.py):**
```python
# Translation service
OLLAMA_TRANSLATION_ENABLED = os.environ.get('OLLAMA_TRANSLATION_ENABLED', 'True').lower() == 'true'
OLLAMA_TRANSLATION_MODEL = os.environ.get('OLLAMA_TRANSLATION_MODEL', 'deepseek-r1:32b')
OLLAMA_TRANSLATION_ENDPOINT = os.environ.get('OLLAMA_TRANSLATION_ENDPOINT', 'http://localhost:11434')
TRANSLATION_CACHE_TTL = int(os.environ.get('TRANSLATION_CACHE_TTL', '604800'))  # 7 days
```

**Implementation checklist:**
- [ ] Create `TranslationService` class
- [ ] Implement `translate_pali_passage()` method
- [ ] Add Ollama API integration
- [ ] Add error handling & fallbacks
- [ ] Add logging with request IDs
- [ ] Add configuration validation

**Acceptance Criteria:**
- [ ] Service can translate a single passage
- [ ] Service handles Ollama unavailable gracefully
- [ ] Service logs all translation attempts
- [ ] Unit tests pass without Ollama running

**Estimated effort:** 2-3 hours

---

#### Task A.2: Create Translation Cache Table

**File:** `backend/scripts/create_translation_cache.sql`

**Purpose:** Persist translations to avoid redundant API calls

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS pali_translations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pali_text TEXT NOT NULL UNIQUE,
    english_translation TEXT NOT NULL,
    reference TEXT,
    model_used TEXT DEFAULT 'deepseek-r1:32b',
    confidence_score REAL DEFAULT 1.0,
    source TEXT DEFAULT 'ollama',  -- 'ollama' or 'db'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY(reference) REFERENCES paragraphs(reference)
);

CREATE INDEX idx_pali_text ON pali_translations(pali_text);
CREATE INDEX idx_created_at ON pali_translations(created_at);
```

**Migration script:**
```python
# File: backend/app/utils/database_migrations.py
def create_translation_cache_table():
    """Create translation cache table if not exists."""
    conn = sqlite3.connect(current_app.config['TIPITAKA_DB_PATH'])
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pali_translations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pali_text TEXT NOT NULL UNIQUE,
            english_translation TEXT NOT NULL,
            reference TEXT,
            model_used TEXT DEFAULT 'deepseek-r1:32b',
            confidence_score REAL DEFAULT 1.0,
            source TEXT DEFAULT 'ollama',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pali_text
        ON pali_translations(pali_text)
    """)
    conn.commit()
    conn.close()
```

**Acceptance Criteria:**
- [ ] Table created successfully
- [ ] Indexes created for performance
- [ ] Migration runs without errors
- [ ] Table persists across restarts

**Estimated effort:** 1 hour

---

#### Task A.3: Integrate TranslationService into App Init

**File:** `backend/app/__init__.py`

**Purpose:** Initialize TranslationService at app startup

**Changes:**
- Create TranslationService instance
- Store in `app.extensions['translation_service']`
- Run migration on startup
- Log initialization status

**Checklist:**
- [ ] TranslationService created and stored in extensions
- [ ] Migration runs automatically
- [ ] Health check includes translation cache status
- [ ] Logs show initialization

**Estimated effort:** 0.5 hours

---

### Phase B: Core Translation Logic (2-3 hours)

#### Task B.1: Implement Ollama Integration

**File:** `backend/app/services/translation_service.py`

**Purpose:** Call Deepseek via Ollama REST API

**Ollama API flow:**
```
POST /api/generate
{
    "model": "deepseek-r1:32b",
    "prompt": "Translate this Pali text to English: [pali_text]",
    "stream": false,
    "temperature": 0.3  # Low temp for consistency
}

Response:
{
    "response": "English translation here",
    "model": "deepseek-r1:32b",
    "created_at": "2026-03-03T...",
    "total_duration": 1234567890  # nanoseconds
}
```

**Implementation:**
```python
def translate_pali_passage(self, pali_text: str, reference: str = None) -> str:
    """
    Translate Pali passage using Deepseek model.

    Strategy:
    1. Check cache (pali_translations table)
    2. If cache hit → return cached translation
    3. If cache miss → call Ollama
    4. Parse response
    5. Store in cache
    6. Return translation
    """
    logger.info(
        "[TranslationService.translate_pali_passage] "
        "pali=%.80r  reference=%s",
        pali_text, reference
    )

    # Step 1: Check cache
    cached = self._check_cache(pali_text)
    if cached:
        logger.debug(
            "[TranslationService.translate_pali_passage] Cache HIT — "
            "returning cached translation"
        )
        return cached

    # Step 2: Validate Ollama available
    if not self._is_ollama_available():
        logger.warning(
            "[TranslationService.translate_pali_passage] Ollama unavailable — "
            "returning original Pali text"
        )
        return pali_text

    # Step 3: Call Deepseek
    try:
        translation = self._call_deepseek(pali_text)

        # Step 4: Validate response
        if not translation or len(translation) < len(pali_text) * 0.5:
            logger.warning(
                "[TranslationService.translate_pali_passage] "
                "Translation too short (possible failure) — "
                "returning original Pali. translation=%.80r", translation
            )
            return pali_text

        # Step 5: Store in cache
        self._save_to_cache(pali_text, translation, reference)

        logger.info(
            "[TranslationService.translate_pali_passage] Translation successful — "
            "cached for future use. translation_len=%d", len(translation)
        )
        return translation

    except Exception as e:
        logger.error(
            "[TranslationService.translate_pali_passage] Translation FAILED — "
            "returning original Pali. error=%s\n%s",
            e, traceback.format_exc()
        )
        return pali_text
```

**Deepseek prompt engineering:**
```python
def _build_translation_prompt(self, pali_text: str) -> str:
    """Build optimized prompt for Deepseek translation."""
    return f"""Translate the following Pali Buddhist text to English.
Keep the translation literal and accurate to preserve the original meaning.
Do not add explanations or commentary.

Pali text:
{pali_text}

English translation:"""
```

**Acceptance Criteria:**
- [ ] Successfully translates single passage
- [ ] Handles Ollama unavailable gracefully
- [ ] Returns original Pali if translation fails
- [ ] Logs translation attempts
- [ ] Response time <5 seconds per passage

**Estimated effort:** 1.5 hours

---

#### Task B.2: Implement Caching Layer

**File:** `backend/app/services/translation_service.py`

**Purpose:** Store translations to avoid redundant API calls

**Methods:**
```python
def _check_cache(self, pali_text: str) -> Optional[str]:
    """Check if translation already cached."""
    conn = sqlite3.connect(current_app.config['TIPITAKA_DB_PATH'])
    conn.row_factory = self._dict_factory
    cursor = conn.cursor()

    cursor.execute("""
        SELECT english_translation FROM pali_translations
        WHERE pali_text = ? AND (expires_at IS NULL OR expires_at > datetime('now'))
    """, (pali_text,))

    result = cursor.fetchone()
    conn.close()
    return result['english_translation'] if result else None

def _save_to_cache(self, pali_text: str, translation: str, reference: str = None):
    """Save translation to cache."""
    conn = sqlite3.connect(current_app.config['TIPITAKA_DB_PATH'])
    cursor = conn.cursor()
    ttl_days = current_app.config.get('TRANSLATION_CACHE_TTL', 7)

    try:
        cursor.execute("""
            INSERT OR REPLACE INTO pali_translations
            (pali_text, english_translation, reference, model_used, source, expires_at)
            VALUES (?, ?, ?, ?, 'ollama', datetime('now', '+' || ? || ' days'))
        """, (pali_text, translation, reference, 'deepseek-r1:32b', ttl_days))

        conn.commit()
        logger.debug(
            "[TranslationService._save_to_cache] Cached translation — "
            "expires_at=+%d days", ttl_days
        )
    except sqlite3.IntegrityError as e:
        logger.warning(
            "[TranslationService._save_to_cache] Cache insert failed (duplicate?) — "
            "error=%s", e
        )
    finally:
        conn.close()
```

**Acceptance Criteria:**
- [ ] Translations cached successfully
- [ ] Cache lookup returns correct translation
- [ ] Cache expiry works correctly
- [ ] Duplicate inserts handled gracefully
- [ ] Cache significantly reduces API calls

**Estimated effort:** 1 hour

---

#### Task B.3: Implement Batch Translation

**File:** `backend/app/services/translation_service.py`

**Purpose:** Translate multiple passages efficiently

**Strategy:**
```python
def enrich_passages_with_translations(
    self,
    passages: List[Dict]
) -> List[Dict]:
    """
    Ensure all passages have english_text.

    For each passage:
    - If english_text exists and non-empty → skip
    - If NULL/empty → translate pali_text
    - Add to passage dict

    Return: modified passages with translations
    """
    logger.info(
        "[TranslationService.enrich_passages_with_translations] "
        "enriching %d passages", len(passages)
    )

    enriched = []
    need_translation = []

    # Classify passages
    for passage in passages:
        if passage.get('english_text'):
            enriched.append(passage)
        else:
            need_translation.append(passage)

    # Batch translate missing ones
    if need_translation:
        logger.info(
            "[TranslationService.enrich_passages_with_translations] "
            "%d passages need translation", len(need_translation)
        )

        for passage in need_translation:
            pali = passage.get('pali_text', '')
            reference = passage.get('reference')

            translation = self.translate_pali_passage(pali, reference)
            passage['english_text'] = translation
            passage['translation_source'] = 'ollama' if translation != pali else 'fallback'

            enriched.append(passage)

    logger.info(
        "[TranslationService.enrich_passages_with_translations] "
        "enriched=%d  with_db_translation=%d  with_deepseek=%d",
        len(enriched),
        len([p for p in enriched if p.get('translation_source') == 'db']),
        len([p for p in enriched if p.get('translation_source') == 'ollama'])
    )

    return enriched
```

**Acceptance Criteria:**
- [ ] All passages have english_text after enrichment
- [ ] DB translations prioritized (not re-translated)
- [ ] Deepseek translations cached
- [ ] Logging shows split between sources
- [ ] Performance acceptable (10-20 passages/sec)

**Estimated effort:** 1 hour

---

### Phase C: Integration (2-3 hours)

#### Task C.1: Integrate into Chat Route

**File:** `backend/app/routes/chat.py`

**Purpose:** Call TranslationService after search, before LLM

**Changes:**
```python
# In chat() route, after STEP 1:

# ── STEP 1: Tipitaka search ───────────────────────────────────────────
logger.info("[chat:%s] STEP 1 — querying Tipitaka for relevant passages...", request_id)
try:
    passages = tipitaka_service.search_relevant_passages(message)
    logger.info(
        "[chat:%s] STEP 1 OK — found %d passage(s).",
        request_id, len(passages),
    )
except Exception as exc:
    logger.error("[chat:%s] STEP 1 FAILED — error=%s\n%s", request_id, exc, traceback.format_exc())
    raise

# ── NEW STEP 1.5: Enrich with translations ──────────────────────────
logger.info("[chat:%s] STEP 1.5 — enriching passages with translations...", request_id)
try:
    translation_service = current_app.extensions.get('translation_service')
    if translation_service:
        passages = translation_service.enrich_passages_with_translations(passages)
        logger.info(
            "[chat:%s] STEP 1.5 OK — enriched %d passages with translations.",
            request_id, len(passages),
        )
    else:
        logger.warning("[chat:%s] STEP 1.5 — translation service not initialized", request_id)
except Exception as exc:
    logger.warning(
        "[chat:%s] STEP 1.5 WARNING — translation enrichment failed (non-critical) — "
        "continuing without translations. error=%s\n%s",
        request_id, exc, traceback.format_exc(),
    )
    # Continue anyway — translations are optional enhancement

# ── STEP 2: Generate LLM response ───────────────────────────────────
# ... existing code ...
```

**Acceptance Criteria:**
- [ ] Translations enriched before LLM
- [ ] Non-fatal if translation fails
- [ ] Logging shows enrichment step
- [ ] Chat still works if translation service unavailable
- [ ] No performance regression

**Estimated effort:** 1 hour

---

#### Task C.2: Add Translation Status to Health Check

**File:** `backend/app/routes/health.py`

**Purpose:** Monitor translation service health

**Changes:**
```python
@health_bp.route('/health/detailed', methods=['GET'])
def health_detailed():
    """Detailed health check including translation service."""
    status = {
        'timestamp': datetime.utcnow().isoformat(),
        'services': {}
    }

    # ... existing checks ...

    # Check translation service
    translation_service = current_app.extensions.get('translation_service')
    try:
        if translation_service and translation_service.is_ollama_available():
            status['services']['translation'] = 'healthy'
        elif translation_service:
            status['services']['translation'] = 'degraded'  # Ollama unavailable
        else:
            status['services']['translation'] = 'unavailable'
    except Exception as e:
        status['services']['translation'] = 'unhealthy'

    return jsonify(status), 200 if all(s == 'healthy' for s in status['services'].values()) else 503
```

**Acceptance Criteria:**
- [ ] Health endpoint reports translation service status
- [ ] Ollama unavailable reported as 'degraded'
- [ ] Endpoint is fast (<100ms)

**Estimated effort:** 0.5 hours

---

#### Task C.3: Add Configuration & Env Vars

**File:** `backend/config/settings.py` and `.env.example`

**Changes:**
```python
# settings.py
class Config:
    # ... existing config ...

    # Translation Service (Deepseek via Ollama)
    OLLAMA_TRANSLATION_ENABLED = os.environ.get(
        'OLLAMA_TRANSLATION_ENABLED', 'True'
    ).lower() == 'true'
    OLLAMA_TRANSLATION_MODEL = os.environ.get(
        'OLLAMA_TRANSLATION_MODEL', 'deepseek-r1:32b'
    )
    OLLAMA_TRANSLATION_ENDPOINT = os.environ.get(
        'OLLAMA_TRANSLATION_ENDPOINT', 'http://localhost:11434'
    )
    OLLAMA_TRANSLATION_TIMEOUT = int(os.environ.get(
        'OLLAMA_TRANSLATION_TIMEOUT', '30'
    ))  # seconds
    TRANSLATION_CACHE_TTL = int(os.environ.get(
        'TRANSLATION_CACHE_TTL', '604800'
    ))  # 7 days in seconds
```

**Acceptance Criteria:**
- [ ] All config vars have sensible defaults
- [ ] Documented in .env.example
- [ ] Environment variables override defaults

**Estimated effort:** 0.5 hours

---

### Phase D: Testing (2-3 hours)

#### Task D.1: Unit Tests for TranslationService

**File:** `backend/tests/test_translation_service.py`

**Test cases:**
```python
def test_translate_pali_passage_success(translation_service):
    """Test successful translation."""
    pali = "metta bhavana"
    result = translation_service.translate_pali_passage(pali)
    assert result
    assert len(result) > len(pali) * 0.5

def test_translate_pali_passage_cache_hit(translation_service):
    """Test cache hit on second call."""
    pali = "samadhi"

    # First call
    result1 = translation_service.translate_pali_passage(pali)

    # Second call should be from cache (faster)
    import time
    start = time.time()
    result2 = translation_service.translate_pali_passage(pali)
    elapsed = time.time() - start

    assert result1 == result2
    assert elapsed < 0.1  # Cache should be instant

def test_translate_pali_passage_ollama_unavailable(translation_service, monkeypatch):
    """Test fallback when Ollama unavailable."""
    pali = "dhamma"

    # Mock Ollama unavailable
    monkeypatch.setattr(translation_service, '_is_ollama_available', lambda: False)

    result = translation_service.translate_pali_passage(pali)
    assert result == pali  # Should return original

def test_enrich_passages_with_translations(translation_service):
    """Test batch enrichment."""
    passages = [
        {'pali_text': 'nirvana', 'english_text': None},
        {'pali_text': 'karma', 'english_text': 'action'},  # Already has translation
    ]

    enriched = translation_service.enrich_passages_with_translations(passages)

    assert len(enriched) == 2
    assert enriched[0]['english_text'] is not None
    assert enriched[1]['english_text'] == 'action'

def test_enrich_passages_performance(translation_service):
    """Test batch translation performance."""
    passages = [{'pali_text': f'word{i}'} for i in range(10)]

    import time
    start = time.time()
    enriched = translation_service.enrich_passages_with_translations(passages)
    elapsed = time.time() - start

    assert len(enriched) == 10
    assert elapsed < 60  # Should complete in under 1 minute for 10 passages
```

**Acceptance Criteria:**
- [ ] 10+ test cases written
- [ ] >80% coverage of TranslationService
- [ ] All tests pass without Ollama running
- [ ] Cache hit test confirms performance gain

**Estimated effort:** 1.5 hours

---

#### Task D.2: Integration Tests

**File:** `backend/tests/test_chat_with_translations.py`

**Test scenarios:**
```python
def test_chat_route_with_missing_translations(app_with_mocks, monkeypatch):
    """Test chat endpoint when passages lack english_text."""
    # Mock search results with NULL english_text
    passages = [
        {
            'pali_text': 'samadhi dhammo',
            'english_text': None,  # Missing
            'reference': 'SN 45.2'
        }
    ]

    # Mock TranslationService
    mock_translation_service = MagicMock()
    mock_translation_service.enrich_passages_with_translations.return_value = [
        {
            **passages[0],
            'english_text': 'Concentration is the dhamma',
            'translation_source': 'ollama'
        }
    ]

    app_with_mocks.extensions['translation_service'] = mock_translation_service

    with app_with_mocks.test_client() as client:
        response = client.post('/api/chat', json={
            'message': 'What is samadhi?',
            'model_id': 'copilot'
        })

    assert response.status_code == 200
    # Verify passages had translations enriched
    mock_translation_service.enrich_passages_with_translations.assert_called_once()

def test_chat_route_fallback_no_translation(app_with_mocks, monkeypatch):
    """Test chat continues if translation service unavailable."""
    app_with_mocks.extensions['translation_service'] = None

    with app_with_mocks.test_client() as client:
        response = client.post('/api/chat', json={
            'message': 'Test question',
            'model_id': 'copilot'
        })

    # Should still work
    assert response.status_code == 200
```

**Acceptance Criteria:**
- [ ] Chat works with translated passages
- [ ] Chat works if translation service unavailable
- [ ] Translation source tracked in response
- [ ] Logging shows translation enrichment

**Estimated effort:** 1 hour

---

### Phase E: Documentation (1 hour)

#### Task E.1: Document Translation Feature

**File:** `docs/TRANSLATION_SERVICE.md`

**Contents:**
```markdown
# Pali Translation Service

## Overview
The Translation Service provides automatic Pali-to-English translation
fallback using Ollama's Deepseek model. When a Tipitaka passage lacks
an English translation in the database, the service translates it
automatically and caches the result.

## Architecture
- Service: `TranslationService`
- Provider: Ollama (Deepseek model)
- Cache: SQLite (pali_translations table)
- Trigger: Automatically after search, before LLM

## Configuration
```

**Sections:**
- Overview
- Architecture diagram
- Configuration reference
- API documentation
- Cache management
- Troubleshooting
- Performance tips
- Example usage

**Acceptance Criteria:**
- [ ] Documentation complete and clear
- [ ] Examples work without changes
- [ ] Configuration options documented
- [ ] Troubleshooting guide included

**Estimated effort:** 1 hour

---

#### Task E.2: Update README & API Docs

**File:** `backend/README.md` and `docs/API_REFERENCE.md`

**Changes:**
- Add Translation Service to overview
- Document new response fields: `translation_source`
- Add configuration examples
- Add health check documentation

**Acceptance Criteria:**
- [ ] Translation feature mentioned in README
- [ ] API docs updated with new fields
- [ ] Configuration examples included

**Estimated effort:** 0.5 hours

---

## 4. Configuration Guide

### 4.1 Enable Translation Feature

**.env file:**
```bash
# Translation Service (Deepseek via Ollama)
OLLAMA_TRANSLATION_ENABLED=True
OLLAMA_TRANSLATION_MODEL=deepseek-r1:32b
OLLAMA_TRANSLATION_ENDPOINT=http://localhost:11434
OLLAMA_TRANSLATION_TIMEOUT=30
TRANSLATION_CACHE_TTL=604800  # 7 days
```

### 4.2 Start Ollama

```bash
# Pull Deepseek model
ollama pull deepseek-r1:32b

# Start Ollama server (runs on port 11434)
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

### 4.3 Verify Installation

```bash
# Test translation endpoint
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-r1:32b",
    "prompt": "Translate to English: metta",
    "stream": false
  }'
```

---

## 5. Performance Characteristics

### 5.1 Translation Time

| Scenario | Time | Notes |
|----------|------|-------|
| Cache hit | <10ms | Instant SQLite lookup |
| First translation | 2-5s | Ollama API call + model inference |
| Batch (10 passages) | 20-50s | Sequential calls |
| Parallel (future) | 5-10s | If implemented async |

### 5.2 Cache Size

```
Estimate:
- Each cached translation: ~200 bytes (Pali + English + metadata)
- 10,000 cached translations: ~2 MB
- 100,000 translations: ~20 MB
```

### 5.3 Optimization Opportunities

1. **Async translations** — Translate in background, improve UX
2. **Batch API** — If Ollama supports batch endpoint
3. **Compression** — Compress cached translations
4. **Smart filtering** — Don't translate very short passages
5. **Fallback models** — Use smaller model if large fails

---

## 6. Quality Assurance

### 6.1 Translation Quality Metrics

Track:
- **Accuracy:** Manual review of sample translations
- **Consistency:** Same passage always translates same way
- **Completeness:** All critical passages have translations
- **Performance:** Response time acceptable

### 6.2 Monitoring

**Health checks:**
- Ollama connectivity
- Cache hit rate
- Average translation time
- Error rate

**Logs to monitor:**
- Translation failures (should be rare)
- Cache misses (should decrease over time)
- Ollama unavailability

### 6.3 Alerts

Setup alerts for:
- Ollama offline for >5 minutes
- Translation success rate <99%
- Cache size >500 MB
- Response time >2 seconds (percentile 95)

---

## 7. Rollout Strategy

### Phase 1: Beta (Internal Testing)
- Enable feature on dev environment only
- Deepseek model: `deepseek-r1:32b` (largest)
- Cache TTL: 24 hours (short for testing)
- Manual QA on 50 passages

### Phase 2: Staging
- Enable on staging environment
- Smaller model: `deepseek-r1:7b` (faster)
- Cache TTL: 7 days
- Monitor for 1 week

### Phase 3: Production
- Gradual rollout (10% users → 50% → 100%)
- Model: `deepseek-r1:7b` (balance speed/quality)
- Cache TTL: 30 days
- Alert on any issues

---

## 8. Fallback & Rollback

### If Translations Degrade Quality:
1. Disable translation service: `OLLAMA_TRANSLATION_ENABLED=False`
2. Restart app (no deployment needed)
3. Investigation window: 24-48 hours
4. Switch to different model if needed

### If Ollama Crashes:
1. Chat still works (passages show original Pali)
2. Frontend shows translation_source='fallback'
3. Alert triggered automatically
4. Operations team restarts Ollama

---

## 9. Success Criteria

### Completion metrics:
- [ ] All 21 tasks completed and tested
- [ ] >80% unit test coverage
- [ ] Integration tests pass
- [ ] Performance benchmarks met (<5s per translation)
- [ ] Documentation complete
- [ ] Zero critical issues in staging
- [ ] Team trained on feature

### User-facing metrics:
- [ ] Translation cache hit rate >90% after 1 week
- [ ] Average chat response time unchanged
- [ ] User satisfaction with translations >4/5
- [ ] Zero data loss from cache
- [ ] Ollama availability >99.5%

---

## 10. Implementation Timeline

| Phase | Tasks | Duration | Status |
|-------|-------|----------|--------|
| A: Infrastructure | 3 | 1-2h | ⏳ Ready |
| B: Translation Logic | 3 | 2-3h | ⏳ Ready |
| C: Integration | 3 | 2-3h | ⏳ Ready |
| D: Testing | 2 | 2-3h | ⏳ Ready |
| E: Documentation | 2 | 1h | ⏳ Ready |
| **TOTAL** | **13** | **8-12h** | ⏳ Ready |

**Team effort:** 1-2 developers, 1 week

---

## 11. Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Ollama unavailable | Medium | Low | Fallback to original Pali |
| Poor translation quality | Low | Medium | Manual QA before production |
| Cache grows unbounded | Low | Medium | TTL + cleanup script |
| Performance regression | Low | High | Load testing required |

### Mitigation Strategy:
1. Non-critical feature (chat works without it)
2. Graceful degradation (fallback to Pali)
3. Staged rollout (catch issues early)
4. Monitoring & alerts (quick response)

---

**Plan Status:** ✅ READY FOR IMPLEMENTATION
**No Changes Made:** ✅ Analysis only
**Next Step:** Team review & approval before starting Phase A

---

*Generated: 2026-03-03 | Analysis: Complete*
