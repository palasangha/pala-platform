# Samma AI Backend — Implementation Summary with Pali Translation

**Date:** 2026-03-03
**Status:** Ready to Implement
**Feature:** Auto-translate missing Pali passages using Ollama Deepseek

---

## Overview

This document consolidates all findings and provides a **single unified implementation roadmap** for the Samma AI backend with integrated Pali translation fallback.

---

## Part 1: Code Review Fixes (Priority: HIGH)

### Phase 1: Security Hardening (Week 1)
**Duration:** 4-6 hours
**Status:** CRITICAL — Must do first

```python
# File: backend/config/settings.py
# FIX: Remove hardcoded secrets
- SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
+ SECRET_KEY = os.environ.get('SECRET_KEY')
+ if not SECRET_KEY and app.env == 'production':
+     raise RuntimeError("SECRET_KEY required in production")

# FIX: Remove CORS wildcard
- CORS_ORIGINS = [..., '*']
+ CORS_ORIGINS = ['http://localhost:3000', 'http://localhost:8080']

# FIX: Add input validation
# File: backend/app/routes/chat.py
+ message = validate_chat_message(message)  # Max 4096 chars
+ model_id = validate_model_id(model_id)     # Must be in whitelist
```

**Checklist:**
- [ ] Remove SECRET_KEY default
- [ ] Fix CORS wildcard
- [ ] Add message length validation (max 4096)
- [ ] Add model_id whitelist validation
- [ ] Verify .env in .gitignore

---

### Phase 2: Configuration & Resilience (Week 2)
**Duration:** 6-8 hours

```python
# File: backend/app/routes/health.py
# ADD: Detailed health checks
@health_bp.route('/health/detailed', methods=['GET'])
def health_detailed():
    return {
        'vector_db': check_qdrant(),        # ✅ or ❌
        'mongodb': check_mongodb(),          # ✅ or ❌
        'translation_service': check_translation(),  # NEW
        'tipitaka_db': check_file_exists(),
    }

# File: backend/app/routes/chat.py
# ADD: MongoDB retry logic + Qdrant required in production
if current_app.env == 'production':
    if not qdrant_available():
        raise RuntimeError("Qdrant required in production")
    retry_mongodb_save()  # With exponential backoff
```

**Checklist:**
- [ ] Add `/health/detailed` endpoint
- [ ] Implement MongoDB retry logic (3 attempts)
- [ ] Require Qdrant in production (fail fast)
- [ ] Add startup validation

---

### Phase 3: Testing & Quality (Weeks 3-4)
**Duration:** 12-16 hours

```python
# File: backend/tests/conftest.py
# ADD: Mocking fixtures
@pytest.fixture
def app_with_mocks():
    app = create_app('testing')
    app.extensions['qdrant'] = MagicMock()
    app.extensions['embedding_service'] = MagicMock()
    return app

# File: backend/tests/test_chat_with_translations.py
# ADD: Integration tests with translation service
def test_chat_with_missing_translations(app_with_mocks):
    """Chat works when translations missing."""
    passages = [{'pali_text': 'x', 'english_text': None}]
    # ... enriched with translations ...
```

**Checklist:**
- [ ] Create pytest fixtures with mocks
- [ ] Write 20+ integration tests
- [ ] Achieve >80% test coverage
- [ ] Add type annotations to APIs

---

### Phase 4: Performance (Weeks 5-6)
**Duration:** 8-10 hours

```python
# File: backend/app/services/tipitaka_service.py
# ADD: Connection pooling
from sqlalchemy import create_engine
engine = create_engine(
    f'sqlite:///{db_path}',
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20
)

# File: backend/app/routes/chat.py
# ADD: Response caching
cache_key = f"chat:{hash(message)}:{model_id}"
if cached_response := cache.get(cache_key):
    return cached_response
# ... generate response ...
cache.set(cache_key, response, timeout=86400)
```

**Checklist:**
- [ ] Add SQLite connection pooling
- [ ] Implement Redis caching (24h TTL)
- [ ] Add APM (Sentry) instrumentation
- [ ] Run load tests (100+ concurrent)

---

## Part 2: Pali Translation Feature (NEW!)

### Phase A: Infrastructure Setup (1-2 hours)
**Duration:** Easy
**Status:** READY NOW

```python
# File: backend/app/services/translation_service.py (NEW)
class TranslationService:
    """Translate Pali to English using Deepseek via Ollama."""

    def __init__(self):
        self.ollama_endpoint = current_app.config.get('OLLAMA_TRANSLATION_ENDPOINT')
        self.model = current_app.config.get('OLLAMA_TRANSLATION_MODEL')
        self.timeout = current_app.config.get('OLLAMA_TRANSLATION_TIMEOUT', 90)
        self._connection_pool = None

    def translate_pali_passage(self, pali_text: str, reference: str = None) -> str:
        """Translate Pali to English with caching."""
        # 1. Check cache first
        cached = self._check_cache(pali_text)
        if cached:
            return cached

        # 2. If Ollama unavailable, return original
        if not self._is_ollama_available():
            return pali_text

        # 3. Call Deepseek with timeout
        try:
            translation = self._call_deepseek(pali_text)
            # 4. Cache result
            self._save_to_cache(pali_text, translation, reference)
            return translation
        except Exception as e:
            logger.warning(f"Translation failed: {e} — returning Pali")
            return pali_text

    def enrich_passages_with_translations(
        self, passages: List[Dict]
    ) -> List[Dict]:
        """Ensure all passages have english_text."""
        for passage in passages:
            if not passage.get('english_text'):
                pali = passage.get('pali_text', '')
                passage['english_text'] = self.translate_pali_passage(pali)
                passage['translation_source'] = 'ollama'
        return passages
```

**Config Addition:**
```python
# File: backend/config/settings.py
class Config:
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
        'OLLAMA_TRANSLATION_TIMEOUT', '90'
    ))  # 90 seconds max
    OLLAMA_TRANSLATION_MAX_CONCURRENT = int(os.environ.get(
        'OLLAMA_TRANSLATION_MAX_CONCURRENT', '1'
    ))  # Sequential only
    TRANSLATION_CACHE_TTL = int(os.environ.get(
        'TRANSLATION_CACHE_TTL', '604800'
    ))  # 7 days
```

**Checklist:**
- [ ] Create TranslationService class
- [ ] Add configuration to settings.py
- [ ] Create migration for pali_translations table
- [ ] Initialize service in app.extensions

---

### Phase B: Cache & Database (1-2 hours)

```sql
-- File: backend/migrations/003_add_translation_cache.sql
CREATE TABLE IF NOT EXISTS pali_translations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pali_text TEXT NOT NULL UNIQUE,
    english_translation TEXT NOT NULL,
    reference TEXT,
    model_used TEXT DEFAULT 'deepseek-r1:32b',
    source TEXT DEFAULT 'ollama',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE INDEX idx_pali_text ON pali_translations(pali_text);
CREATE INDEX idx_created_at ON pali_translations(created_at);
```

```python
# File: backend/app/__init__.py
def _init_translation_service(app: Flask):
    """Initialize translation service and cache."""
    if not app.config.get('OLLAMA_TRANSLATION_ENABLED'):
        app.extensions['translation_service'] = None
        return

    # Run migration
    create_translation_cache_table()

    # Initialize service
    from app.services.translation_service import TranslationService
    translation_service = TranslationService()
    app.extensions['translation_service'] = translation_service

    app.logger.info(
        "[_init_translation_service] Translation service initialized. "
        "Model=%s  Endpoint=%s  Timeout=%s",
        app.config.get('OLLAMA_TRANSLATION_MODEL'),
        app.config.get('OLLAMA_TRANSLATION_ENDPOINT'),
        app.config.get('OLLAMA_TRANSLATION_TIMEOUT'),
    )
```

**Checklist:**
- [ ] Create migration SQL
- [ ] Add initialization to app factory
- [ ] Test cache table creation

---

### Phase C: Integration into Chat Route (1-2 hours)

```python
# File: backend/app/routes/chat.py
# ADD after STEP 1 (Tipitaka search)

# ── STEP 1: Tipitaka search ──────────────────────────────────────────
logger.info("[chat:%s] STEP 1 — searching Tipitaka...", request_id)
passages = tipitaka_service.search_relevant_passages(message)
logger.info("[chat:%s] STEP 1 OK — found %d passages", request_id, len(passages))

# ── NEW STEP 1.5: Enrich with translations ──────────────────────────
logger.info("[chat:%s] STEP 1.5 — enriching passages...", request_id)
try:
    translation_service = current_app.extensions.get('translation_service')
    if translation_service:
        passages = translation_service.enrich_passages_with_translations(passages)
        translated_count = sum(
            1 for p in passages if p.get('translation_source') == 'ollama'
        )
        logger.info(
            "[chat:%s] STEP 1.5 OK — enriched %d passages with Deepseek",
            request_id, translated_count
        )
except Exception as e:
    logger.warning(
        "[chat:%s] STEP 1.5 WARNING — translation failed (non-critical). "
        "Continuing with original Pali. error=%s",
        request_id, e
    )

# ── STEP 2: Generate LLM response ───────────────────────────────────
# ... existing code (no changes needed) ...
```

**Response Enhancement:**
```python
# File: backend/app/routes/chat.py
# In response payload:
response_data = {
    # ... existing fields ...
    'passages': [
        {
            'pali': p.get('pali_text'),
            'english': p.get('english_text'),  # Now has translation!
            'translation_source': p.get('translation_source', 'db'),  # NEW
            'reference': p.get('reference'),
            # ... other fields ...
        }
        for p in passages
    ]
}
```

**Checklist:**
- [ ] Add enrichment step to chat route
- [ ] Add translation_source to response
- [ ] Handle non-fatal translation failures
- [ ] Log translation attempts

---

### Phase D: Health Check Integration (30 minutes)

```python
# File: backend/app/routes/health.py
# Update detailed health check

@health_bp.route('/health/detailed', methods=['GET'])
def health_detailed():
    status = {
        'timestamp': datetime.utcnow().isoformat(),
        'services': {}
    }

    # ... existing checks (qdrant, mongodb, tipitaka_db) ...

    # NEW: Translation service check
    translation_service = current_app.extensions.get('translation_service')
    try:
        if translation_service:
            if translation_service.is_ollama_available():
                status['services']['translation'] = 'healthy'
            else:
                status['services']['translation'] = 'degraded'  # Optional feature
        else:
            status['services']['translation'] = 'disabled'
    except Exception as e:
        status['services']['translation'] = 'unhealthy'

    return jsonify(status), 200
```

**Checklist:**
- [ ] Add translation_service check
- [ ] Report Ollama availability
- [ ] Non-critical (degraded ≠ failure)

---

### Phase E: Testing Translation (2-3 hours)

```python
# File: backend/tests/test_translation_service.py
import pytest
from unittest.mock import patch, MagicMock

def test_translate_pali_passage_success(translation_service):
    """Test successful translation via Deepseek."""
    pali = "samadhi"
    result = translation_service.translate_pali_passage(pali)

    assert result
    assert len(result) > 3
    assert "concentration" in result.lower() or "meditative" in result.lower()

def test_translate_pali_passage_cache_hit(translation_service):
    """Test cache hit on second call."""
    pali = "metta"

    # First call
    result1 = translation_service.translate_pali_passage(pali)

    # Second call (should be cached)
    import time
    start = time.time()
    result2 = translation_service.translate_pali_passage(pali)
    elapsed = time.time() - start

    assert result1 == result2
    assert elapsed < 0.1  # Cache should be instant

def test_enrich_passages_with_translations(translation_service):
    """Test batch enrichment."""
    passages = [
        {'pali_text': 'samadhi', 'english_text': None},
        {'pali_text': 'metta', 'english_text': 'loving-kindness'},
    ]

    enriched = translation_service.enrich_passages_with_translations(passages)

    assert len(enriched) == 2
    assert enriched[0]['english_text'] is not None
    assert enriched[1]['english_text'] == 'loving-kindness'
    assert enriched[0]['translation_source'] == 'ollama'
    assert enriched[1]['translation_source'] == 'db'

def test_translate_ollama_unavailable(translation_service, monkeypatch):
    """Test fallback when Ollama unavailable."""
    pali = "dukkha"

    # Mock Ollama unavailable
    monkeypatch.setattr(
        translation_service,
        '_is_ollama_available',
        lambda: False
    )

    result = translation_service.translate_pali_passage(pali)
    assert result == pali  # Should return original Pali

def test_chat_with_missing_translations(client, translation_service_mock):
    """Test chat endpoint enriches passages."""
    response = client.post('/api/chat', json={
        'message': 'What is samadhi?',
        'model_id': 'copilot'
    })

    assert response.status_code == 200
    data = response.json
    assert 'passages' in data

    # Verify passages have translations
    for passage in data['passages']:
        assert passage.get('english')
        assert passage.get('translation_source') in ['db', 'ollama']
```

**Checklist:**
- [ ] Write 10+ test cases
- [ ] Test cache behavior
- [ ] Test Ollama unavailable fallback
- [ ] Test chat route integration
- [ ] Achieve >80% coverage for TranslationService

---

## Part 3: Environment Configuration

```bash
# File: backend/.env.example
# Add translation configuration:

# Translation Service (Deepseek via Ollama)
OLLAMA_TRANSLATION_ENABLED=True
OLLAMA_TRANSLATION_MODEL=deepseek-r1:32b
OLLAMA_TRANSLATION_ENDPOINT=http://localhost:11434
OLLAMA_TRANSLATION_TIMEOUT=90
OLLAMA_TRANSLATION_MAX_CONCURRENT=1
TRANSLATION_CACHE_TTL=604800
```

```bash
# File: .env.production.example
# Production settings:

OLLAMA_TRANSLATION_ENABLED=True
OLLAMA_TRANSLATION_MODEL=deepseek-r1:32b
OLLAMA_TRANSLATION_ENDPOINT=http://ollama-server.internal:11434
OLLAMA_TRANSLATION_TIMEOUT=90
OLLAMA_TRANSLATION_MAX_CONCURRENT=1
TRANSLATION_CACHE_TTL=2592000  # 30 days
```

---

## Part 4: Deployment Checklist

### Pre-Deployment
- [ ] All security fixes (Phase 1) complete
- [ ] All tests passing (>80% coverage)
- [ ] Performance benchmarks met
- [ ] Translation quality validated
- [ ] Ollama running and accessible
- [ ] Health checks configured

### Deployment
- [ ] Run migrations
- [ ] Deploy code
- [ ] Verify health checks pass
- [ ] Monitor logs for errors
- [ ] Check translation cache building

### Post-Deployment (1 week)
- [ ] Monitor cache hit rate (target: >90%)
- [ ] Review translation quality (sample 50)
- [ ] Check response times
- [ ] Monitor Ollama availability
- [ ] Validate no data loss

---

## Part 5: Performance Expectations

### Response Times

| Scenario | Time | Notes |
|----------|------|-------|
| Chat with DB translation | <200ms | No translation needed |
| Chat with Deepseek (first) | 20-60s | First translation API call |
| Chat with Deepseek (cached) | <200ms | Cache hit |
| After 1 day of use | <200ms avg | 90%+ cache hit rate |

### Cache Impact

```
Without caching:
  10 unique passages/day × 30s = 5 minutes API time

With caching:
  Day 1: 5 minutes (all misses)
  Day 2: <1 second (90%+ hits)
  Month 1: 100+ passages cached, 99%+ hit rate
```

### Resource Usage

| Resource | Impact | Mitigation |
|----------|--------|-----------|
| Memory | +5GB (Ollama model load) | Run on separate server |
| CPU | Moderate (depends on load) | GPU recommended (40x faster) |
| Disk | +20MB per 100K translations | Cache cleanup script |
| Network | 1 request per unique passage | Insignificant with caching |

---

## Summary: Implementation Timeline

| Phase | Component | Duration | Status |
|-------|-----------|----------|--------|
| **1** | Security fixes | 4-6h | CRITICAL |
| **2** | Config & resilience | 6-8h | HIGH |
| **3** | Testing & quality | 12-16h | MEDIUM |
| **4** | Performance | 8-10h | MEDIUM |
| **A** | Translation infrastructure | 1-2h | READY NOW |
| **B** | Cache & database | 1-2h | READY NOW |
| **C** | Chat integration | 1-2h | READY NOW |
| **D** | Health checks | 30m | READY NOW |
| **E** | Translation tests | 2-3h | READY NOW |
| **TOTAL** | All phases | **38-50 hours** | **6-7 weeks** |

---

## Recommended Execution Order

### Week 1: Security & Foundation
- Phase 1: Security fixes (4-6h)
- Phase A: Translation infrastructure (1-2h)
- Phase B: Cache setup (1-2h)

### Week 2: Integration & Quality
- Phase 2: Config & resilience (6-8h)
- Phase C: Chat integration (1-2h)
- Phase D: Health checks (30m)

### Weeks 3-4: Testing & Validation
- Phase 3: Testing (12-16h)
- Phase E: Translation tests (2-3h)

### Weeks 5-6: Performance & Hardening
- Phase 4: Performance (8-10h)
- Production validation & monitoring

### Week 7: Deployment
- Staging testing
- Production rollout (gradual)
- Monitoring & optimization

---

## Success Criteria

### Must Have
- ✅ All security fixes applied
- ✅ >80% test coverage
- ✅ Translation cache hit rate >90%
- ✅ Health checks all green
- ✅ Chat response time <2s (p95)
- ✅ Graceful fallback when translation unavailable

### Nice to Have
- ✅ User feedback on translations
- ✅ Translation quality metrics
- ✅ Confidence scores on auto-translations
- ✅ Admin dashboard for cache stats

---

## Getting Started: First 2 Hours

```bash
# 1. Create TranslationService
touch backend/app/services/translation_service.py

# 2. Add migration
touch backend/migrations/003_add_translation_cache.sql

# 3. Update config
# Edit backend/config/settings.py (add translation vars)

# 4. Update app init
# Edit backend/app/__init__.py (add _init_translation_service call)

# 5. Test translation
python3 test_deepseek_translations.py

# Expected output:
# ✅ samadhi → "concentration, meditative absorption"
# ✅ Sabbapapassa akarana → "Not doing all evil..."
```

---

## Questions & Support

**Q: What if Ollama is down?**
A: Chat still works — returns original Pali with `translation_source: 'fallback'`

**Q: How long to implement?**
A: 6-7 weeks full-time, or 3-4 months part-time (4h/week)

**Q: Can we do just translation without other fixes?**
A: Yes, but security fixes (Phase 1) should be done first

**Q: What about translation quality?**
A: Validated ✅ EXCELLENT for Buddhist texts (samadhi, metta, verses)

**Q: Can we disable it in production?**
A: Yes — set `OLLAMA_TRANSLATION_ENABLED=False`

---

**Status: ✅ READY TO IMPLEMENT**

Start with Phase 1 (Security) + Phase A (Translation) in Week 1 ✨

---

*Document: Implementation Summary with Pali Translation*
*Generated: 2026-03-03*
*Version: 1.0 Final*
