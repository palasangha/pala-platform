# Samma AI — Implementation Plan for Code Review Fixes

**Created:** 2026-03-03
**Total Effort:** 30-45 hours (3-5 development days)
**Phases:** 5 (Security → Config → Testing → Performance → Docs)

---

## Phase 1: Security Hardening (Priority: CRITICAL)

**Duration:** 4-6 hours
**Status:** Not Started
**Dependencies:** None

### Task 1.1: Remove Hardcoded SECRET_KEY

**File:** `backend/config/settings.py`

**Current Code:**
```python
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
```

**Required Changes:**
- Remove default value
- Add validation in `DevelopmentConfig` to allow empty for dev
- Add validation in `ProductionConfig` to REQUIRE secret key
- Raise `RuntimeError` if not set in production

**Acceptance Criteria:**
- [ ] Production fails to start without SECRET_KEY env var
- [ ] Development can run with generated random key
- [ ] Test suite passes with mocked secret key

**Estimated Effort:** 1 hour

---

### Task 1.2: Fix CORS Configuration

**File:** `backend/config/settings.py`

**Current Code:**
```python
CORS_ORIGINS = ['http://localhost:8080', 'http://localhost:3000', 'http://localhost:41081', 'http://localhost:12345', '*']
```

**Required Changes:**
- Remove wildcard (`'*'`) from all configs
- Update DevelopmentConfig: use explicit localhost URLs only
- Update ProductionConfig: require CORS_ORIGINS from env, no default wildcard
- Document pattern in `.env.example`

**Acceptance Criteria:**
- [ ] No `'*'` in any CORS config
- [ ] ProductionConfig fails if CORS_ORIGINS not set
- [ ] DevelopmentConfig uses specific URLs: `['http://localhost:3000', 'http://localhost:8080']`
- [ ] Unit test verifies no wildcard

**Estimated Effort:** 1 hour

---

### Task 1.3: Add Message Validation

**File:** `backend/app/routes/chat.py`

**Current Code:**
```python
message = data['message']  # No validation
```

**Required Changes:**
- Validate message length: max 4096 chars
- Validate message type: must be string
- Reject suspicious patterns: "system:", "ignore:", "override:"
- Log validation failures with warning level

**Implementation:**
```python
# Add validation helper in utils
def validate_chat_message(message: str) -> Tuple[bool, Optional[str]]:
    """Validate user message for security and sanity."""
    if not isinstance(message, str):
        return False, "Message must be a string"
    if len(message) > 4096:
        return False, "Message exceeds 4096 character limit"
    if len(message.strip()) == 0:
        return False, "Message cannot be empty"
    suspicious_patterns = ['system:', 'ignore:', 'override:', 'forget:']
    if any(pat in message.lower() for pat in suspicious_patterns):
        return False, "Message contains suspicious patterns"
    return True, None

# In chat route:
is_valid, error = validate_chat_message(message)
if not is_valid:
    logger.warning("[chat:%s] Message validation failed: %s", request_id, error)
    return jsonify({'error': error}), 400
```

**Acceptance Criteria:**
- [ ] Messages >4096 chars rejected with 400
- [ ] Non-string messages rejected with 400
- [ ] Suspicious patterns rejected with 400
- [ ] Empty strings rejected with 400
- [ ] Valid messages pass through
- [ ] Integration tests cover 5 rejection scenarios

**Estimated Effort:** 1.5 hours

---

### Task 1.4: Add Model ID Whitelist Validation

**File:** `backend/app/routes/chat.py`

**Current Code:**
```python
model_id = data.get('model_id', 'copilot')
```

**Required Changes:**
- Create whitelist of supported models in config
- Validate model_id against whitelist
- Return 400 if invalid
- Document available models in API docs

**Implementation:**
```python
# In settings.py
SUPPORTED_MODELS = ['copilot', 'claude', 'openai', 'ollama']

# In chat route
SUPPORTED_MODELS = current_app.config.get('SUPPORTED_MODELS', ['copilot', 'claude', 'openai'])
if model_id not in SUPPORTED_MODELS:
    logger.warning("[chat:%s] Invalid model_id: %s (supported: %s)",
                   request_id, model_id, SUPPORTED_MODELS)
    return jsonify({'error': f'Model {model_id} not supported'}), 400
```

**Acceptance Criteria:**
- [ ] Only whitelisted models accepted
- [ ] Invalid models return 400 with error message
- [ ] All supported models can be requested
- [ ] API documentation lists available models

**Estimated Effort:** 1 hour

---

### Task 1.5: Verify .gitignore Includes .env

**File:** `backend/.gitignore`

**Required Changes:**
- Ensure `.env` is in gitignore
- Add `.env.local`, `.env.*.local` patterns
- Document secret handling in README

**Acceptance Criteria:**
- [ ] `.env` in .gitignore
- [ ] No `.env` files in git history
- [ ] `.env.example` exists as template
- [ ] SECURITY.md documents secret rotation

**Estimated Effort:** 0.5 hours

---

## Phase 2: Configuration & Resilience (Priority: HIGH)

**Duration:** 6-8 hours
**Status:** Not Started
**Dependencies:** Phase 1 complete

### Task 2.1: Add Health Check Endpoint

**File:** `backend/app/routes/health.py`

**Current Implementation:** Basic `/health` endpoint exists

**Required Changes:**
- Extend health endpoint to check:
  - Qdrant availability (connectivity)
  - MongoDB availability (ping)
  - Tipitaka DB file accessible (stat check)
  - Vector search enabled/disabled status
- Return detailed JSON with component status
- Return 503 if any critical service unavailable

**Implementation:**
```python
@health_bp.route('/health/detailed', methods=['GET'])
def health_detailed():
    """Detailed health check for monitoring."""
    status = {
        'timestamp': datetime.utcnow().isoformat(),
        'services': {}
    }

    # Check Qdrant
    qdrant = current_app.extensions.get('qdrant')
    try:
        if qdrant:
            qdrant.get_collections()
            status['services']['vector_db'] = 'healthy'
        else:
            status['services']['vector_db'] = 'unavailable'
    except Exception as e:
        status['services']['vector_db'] = 'unhealthy'

    # Check MongoDB
    try:
        mongo.db.command('ping')
        status['services']['mongodb'] = 'healthy'
    except Exception as e:
        status['services']['mongodb'] = 'unhealthy'

    # Check Tipitaka DB
    try:
        db_path = current_app.config.get('TIPITAKA_DB_PATH')
        os.stat(db_path)
        status['services']['tipitaka_db'] = 'healthy'
    except Exception as e:
        status['services']['tipitaka_db'] = 'unavailable'

    status_code = 200 if all(
        s == 'healthy' for s in status['services'].values()
    ) else 503

    return jsonify(status), status_code
```

**Acceptance Criteria:**
- [ ] `/health/detailed` returns JSON with all services
- [ ] Returns 200 if all healthy
- [ ] Returns 503 if any critical service unhealthy
- [ ] Endpoint can be called every 10 seconds without performance impact
- [ ] Integration test verifies endpoint behavior

**Estimated Effort:** 2 hours

---

### Task 2.2: Add MongoDB Retry Logic

**File:** `backend/app/routes/chat.py`

**Current Code:**
```python
except Exception as mongo_error:
    logger.warning("[chat:%s] STEP 4 WARNING — MongoDB save failed (non-fatal)...")
    # Just logs and continues
```

**Required Changes:**
- Implement exponential backoff retry (3 attempts, max 5s total)
- In production: fail the request if MongoDB unavailable
- In development: log and continue
- Track retry attempts in logs

**Implementation:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def save_conversation_to_mongodb(conversation_data: Dict) -> str:
    """Save conversation with retry logic."""
    response = mongo.db.conversations.insert_one(conversation_data)
    return str(response.inserted_id)

# In chat route
if current_app.config.get('ENV') == 'production':
    # Production: fail if MongoDB unavailable
    try:
        save_conversation_to_mongodb({...})
    except Exception as e:
        logger.error("[chat:%s] MongoDB persistence failed in production", request_id)
        return jsonify({'error': 'Database unavailable'}), 503
else:
    # Development: continue on failure
    try:
        save_conversation_to_mongodb({...})
    except Exception as e:
        logger.warning("[chat:%s] MongoDB save failed (non-fatal)", request_id)
```

**Acceptance Criteria:**
- [ ] MongoDB retries 3 times on failure
- [ ] Production fails request if all retries exhausted
- [ ] Development logs warning but continues
- [ ] Exponential backoff increases wait time
- [ ] Integration test mocks MongoDB failure and verifies retry

**Estimated Effort:** 2 hours

---

### Task 2.3: Require Qdrant in Production

**File:** `backend/app/__init__.py`

**Current Code:**
```python
except Exception as exc:
    app.logger.warning("[_init_vector_search] STEP 2 FAILED...")
    _set_fallback(app)
    return
```

**Required Changes:**
- Check environment (development vs. production)
- In production: raise exception and fail startup if Qdrant unavailable
- In development: log warning and continue with fallback
- Add startup validation check

**Implementation:**
```python
def _init_vector_search(app: Flask) -> None:
    """Initialize vector search. Fail fast in production if unavailable."""
    # ... existing code ...

    try:
        qdrant = QdrantClient(host=qdrant_host, port=qdrant_port)
        qdrant.get_collections()
    except Exception as exc:
        if app.config.get('ENV') == 'production':
            app.logger.critical(
                "[_init_vector_search] CRITICAL: Qdrant unavailable in production. "
                "Cannot start application."
            )
            raise RuntimeError(f"Qdrant required in production: {exc}") from exc
        else:
            app.logger.warning("[_init_vector_search] STEP 2 FAILED (dev fallback)")
            _set_fallback(app)
            return
```

**Acceptance Criteria:**
- [ ] Production fails to start if Qdrant unavailable
- [ ] Development logs warning and continues
- [ ] Error message is clear and actionable
- [ ] Integration test verifies behavior for both envs

**Estimated Effort:** 1.5 hours

---

### Task 2.4: Add Startup Validation

**File:** `backend/app/__init__.py`

**Required Changes:**
- Run validation before returning app
- Check critical paths exist (DB file, config values)
- Log validation results at startup
- Fail if validation fails in production

**Acceptance Criteria:**
- [ ] Validates TIPITAKA_DB_PATH exists
- [ ] Validates all required env vars set
- [ ] Logs results with clear messages
- [ ] Production fails if validation fails

**Estimated Effort:** 1 hour

---

## Phase 3: Testing & Code Quality (Priority: MEDIUM)

**Duration:** 12-16 hours
**Status:** Not Started
**Dependencies:** Phase 1-2 complete

### Task 3.1: Create pytest Fixtures for Mocking

**File:** `backend/tests/conftest.py`

**Current Code:** Basic fixture setup exists

**Required Changes:**
- Add fixtures for mocking:
  - `qdrant_mock` — Mock Qdrant client
  - `embedding_service_mock` — Mock EmbeddingService
  - `mongo_mock` — Mock MongoDB
  - `model_router_mock` — Mock ModelRouterService
  - `app_with_mocks` — Flask app with all mocks
- Use `pytest-mock` and `mongomock` packages

**Implementation:**
```python
import pytest
from unittest.mock import MagicMock, patch
from mongomock import MongoClient

@pytest.fixture
def qdrant_mock():
    mock = MagicMock()
    mock.get_collections.return_value = []
    mock.search.return_value = []
    return mock

@pytest.fixture
def embedding_service_mock():
    mock = MagicMock()
    mock.encode.return_value = [0.1] * 1024
    mock.ensure_collection.return_value = None
    return mock

@pytest.fixture
def mongo_mock():
    return MongoClient()

@pytest.fixture
def app_with_mocks(qdrant_mock, embedding_service_mock, mongo_mock):
    app = create_app('testing')
    app.extensions['qdrant'] = qdrant_mock
    app.extensions['embedding_service'] = embedding_service_mock

    with patch('app.mongo', mongo_mock):
        yield app
```

**Acceptance Criteria:**
- [ ] All fixtures work without external services
- [ ] Tests run in <5 seconds per file
- [ ] No side effects between tests
- [ ] CI/CD runs tests in isolation (no real DB connections)

**Estimated Effort:** 3 hours

---

### Task 3.2: Write Integration Tests for Fallback Paths

**File:** `backend/tests/test_fallback_paths.py` (NEW)

**Required Changes:**
- Test chat endpoint with Qdrant disabled
- Test vector search → FTS5 → keyword fallback chain
- Test empty passages handling
- Test malformed LLM responses

**Implementation:**
```python
def test_chat_with_qdrant_disabled(app_with_mocks):
    """Test chat works when Qdrant is unavailable."""
    app_with_mocks.extensions['qdrant'] = None

    with app_with_mocks.test_client() as client:
        response = client.post('/api/chat', json={
            'message': 'What is metta?',
            'model_id': 'copilot'
        })

    assert response.status_code == 200
    assert 'passages' in response.json

def test_zero_passages_warning(app_with_mocks, caplog):
    """Test warning logged when no passages found."""
    # Mock search to return empty
    app_with_mocks.extensions['qdrant'].search.return_value = []

    with app_with_mocks.test_client() as client:
        response = client.post('/api/chat', json={
            'message': 'xyz nonsense word',
            'model_id': 'copilot'
        })

    assert 'zero passages returned' in caplog.text

def test_malformed_response_handling(app_with_mocks):
    """Test handling of LLM response missing sections."""
    # Mock response with missing section
    with patch('app.services.model_router_service.ModelRouterService.generate_dhamma_response') as mock:
        mock.return_value = {
            'canonical_teachings': [],  # Missing other sections
            'raw_response': 'invalid'
        }

        with app_with_mocks.test_client() as client:
            response = client.post('/api/chat', json={
                'message': 'Test',
                'model_id': 'copilot'
            })

        assert response.status_code == 200
        # Verify warning was logged
```

**Acceptance Criteria:**
- [ ] 10+ integration tests written
- [ ] Tests cover fallback chain (vector→FTS5→keyword)
- [ ] Tests cover error scenarios
- [ ] Tests run without external services
- [ ] All tests pass

**Estimated Effort:** 4 hours

---

### Task 3.3: Add Type Annotations

**File:** `backend/app/**/*.py`

**Required Changes:**
- Add type hints to all public APIs
- Add return type hints to route handlers
- Add parameter types to service methods
- Use `Optional`, `List`, `Dict` from `typing`

**Target Coverage:**
- Routes: 100% annotations
- Service classes: 100% public methods
- Utility functions: 100%

**Example:**
```python
# Before
def search_relevant_passages(self, query, limit=10):
    passages = []
    # ...
    return passages

# After
def search_relevant_passages(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    passages: List[Dict[str, Any]] = []
    # ...
    return passages
```

**Acceptance Criteria:**
- [ ] All route handlers have type hints
- [ ] All service methods have type hints
- [ ] Type checking passes with `mypy` in strict mode
- [ ] No `Any` types except where necessary

**Estimated Effort:** 3 hours

---

### Task 3.4: Achieve 80%+ Test Coverage

**File:** `backend/tests/`

**Current Coverage:** ~45%

**Required Changes:**
- Identify untested code paths
- Write parametrized tests for edge cases
- Target 80%+ line coverage on core modules

**Tool:** `pytest-cov`

```bash
pytest --cov=app --cov-report=html backend/tests/
# Should show >80% coverage on app/ directory
```

**Acceptance Criteria:**
- [ ] `pytest --cov` reports >80% on core modules
- [ ] HTML coverage report uploaded to CI
- [ ] New code must have >90% coverage

**Estimated Effort:** 4 hours

---

## Phase 4: Performance & Scalability (Priority: MEDIUM)

**Duration:** 8-10 hours
**Status:** Not Started
**Dependencies:** Phase 1-3 complete

### Task 4.1: Add SQLite Connection Pooling

**File:** `backend/app/services/tipitaka_service.py`

**Current Code:**
```python
def _get_connection(self):
    return sqlite3.connect(self.db_path)
```

**Required Changes:**
- Use SQLAlchemy or `sqlalchemy-utils` for connection pooling
- Or implement thread-local caching
- Set max pool size based on worker count
- Add connection timeout

**Implementation (SQLAlchemy):**
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

class TipitakaService:
    _engine = None

    @classmethod
    def get_engine(cls):
        if cls._engine is None:
            db_path = current_app.config.get('TIPITAKA_DB_PATH')
            cls._engine = create_engine(
                f'sqlite:///{db_path}',
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=False
            )
        return cls._engine

    def _get_connection(self):
        return self.get_engine().raw_connection()
```

**Acceptance Criteria:**
- [ ] Connection pool initialized at app startup
- [ ] Pool size configurable via env var
- [ ] Pool pre-pings connections (connection=True)
- [ ] Benchmark shows <50ms per query (previously 100-200ms)
- [ ] Load test passes with 100+ concurrent requests

**Estimated Effort:** 2 hours

---

### Task 4.2: Add Response Caching

**File:** `backend/app/routes/chat.py` and new `backend/app/utils/cache.py`

**Required Changes:**
- Cache identical chat responses (same message, same model)
- Use Redis (or in-memory for dev)
- Set cache TTL: 24 hours
- Add cache invalidation strategy

**Implementation:**
```python
import hashlib
from flask_caching import Cache

cache = Cache(config={'CACHE_TYPE': 'redis', 'CACHE_REDIS_URL': 'redis://localhost:6379'})

def get_cache_key(message: str, model_id: str) -> str:
    """Generate deterministic cache key."""
    return f"chat:{hashlib.md5(f'{message}:{model_id}'.encode()).hexdigest()}"

@chat_bp.route('/chat', methods=['POST'])
def chat():
    # ... validation ...

    cache_key = get_cache_key(message, model_id)
    cached = cache.get(cache_key)
    if cached:
        logger.info("[chat:%s] Cache hit for message", request_id)
        return jsonify(cached)

    # ... generate response ...

    cache.set(cache_key, response_data, timeout=86400)  # 24h
    return jsonify(response_data)
```

**Acceptance Criteria:**
- [ ] Identical requests return cached response
- [ ] Cache key is deterministic
- [ ] Cache TTL configurable
- [ ] Benchmark shows 10-50x faster for cached requests
- [ ] Cache works in dev (in-memory) and prod (Redis)

**Estimated Effort:** 2 hours

---

### Task 4.3: Add APM Instrumentation

**File:** `backend/app/__init__.py` and new `backend/app/utils/instrumentation.py`

**Required Changes:**
- Add Sentry SDK for error tracking
- Add timing instrumentation for critical paths
- Track metrics: response time, passages found, model routing
- Add distributed tracing

**Implementation:**
```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

def create_app(config_name='development'):
    # ... existing code ...

    if app.config.get('SENTRY_DSN'):
        sentry_sdk.init(
            dsn=app.config.get('SENTRY_DSN'),
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.1,
            environment=app.config.get('ENV', 'development')
        )

    return app

# Decorators for timing
from functools import wraps
import time

def track_timing(operation_name: str):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = f(*args, **kwargs)
                duration = time.time() - start
                logger.info(f"[timing] {operation_name} took {duration:.2f}s")
                return result
            except Exception as e:
                duration = time.time() - start
                logger.error(f"[timing] {operation_name} failed after {duration:.2f}s: {e}")
                raise
        return wrapper
    return decorator

# Usage:
@track_timing("search_relevant_passages")
def search_relevant_passages(self, query: str) -> List[Dict]:
    # ...
```

**Acceptance Criteria:**
- [ ] Sentry DSN configurable via env var
- [ ] All errors reported to Sentry
- [ ] Critical paths timed and logged
- [ ] No performance regression (<5% overhead)
- [ ] CI/CD environment variable set correctly

**Estimated Effort:** 2 hours

---

### Task 4.4: Benchmark & Load Testing

**File:** `backend/tests/test_performance.py` (NEW)

**Required Changes:**
- Create load test script (simulates 100+ concurrent requests)
- Benchmark response times before/after optimization
- Verify no regression in latency
- Document baseline metrics

**Implementation:**
```bash
# Using Apache Bench or locust
ab -n 1000 -c 100 -p payload.json -T application/json http://localhost:5000/api/chat

# Or using locust:
locust -f locustfile.py -u 100 -r 10 --run-time 5m
```

**Acceptance Criteria:**
- [ ] Baseline latency measured and documented
- [ ] After Phase 4: latency should decrease by 10-30%
- [ ] 99th percentile response time <2s
- [ ] No crashes under 100 concurrent users
- [ ] Benchmark script integrated into CI

**Estimated Effort:** 2 hours

---

## Phase 5: Documentation & Deployment (Priority: LOW)

**Duration:** 4-6 hours
**Status:** Not Started
**Dependencies:** Phase 1-4 complete

### Task 5.1: Document Secret Rotation Procedures

**File:** `docs/SECURITY.md` (NEW)

**Content:**
- How to rotate SECRET_KEY
- How to rotate API keys (Anthropic, OpenAI)
- Schedule: weekly for dev, quarterly for prod
- Process: generate new key, update env vars, restart app
- Rollback procedure
- Audit trail

**Acceptance Criteria:**
- [ ] Document is clear and actionable
- [ ] Non-technical stakeholders can follow it
- [ ] Script provided to automate rotation
- [ ] Team has acknowledged and signed off

**Estimated Effort:** 1 hour

---

### Task 5.2: Add Deployment Checklist

**File:** `docs/DEPLOYMENT_CHECKLIST.md` (NEW)

**Content:**
- Pre-deployment validation (tests, linting, security scan)
- Deployment steps (build, push, deploy)
- Post-deployment verification (health checks, smoke tests)
- Rollback procedure
- Communication template

**Checklist Items:**
```markdown
## Pre-Deployment
- [ ] All tests pass
- [ ] Code review approved
- [ ] Security scan passed
- [ ] Documentation updated
- [ ] Secrets configured in target env

## Deployment
- [ ] Create backup of database
- [ ] Build Docker image
- [ ] Push to registry
- [ ] Deploy to staging
- [ ] Run smoke tests on staging
- [ ] Deploy to production
- [ ] Health check passes
- [ ] Monitor error rates for 10 minutes

## Rollback
- [ ] Roll back deployment
- [ ] Verify health checks pass
- [ ] Restore from database backup
```

**Acceptance Criteria:**
- [ ] Checklist is comprehensive
- [ ] Can be followed step-by-step
- [ ] Team trained on procedure

**Estimated Effort:** 1.5 hours

---

### Task 5.3: Create Production Configuration Example

**File:** `backend/.env.production.example` (NEW)

**Content:**
- All required env vars with production-safe defaults
- Comments explaining each setting
- Examples of secure values
- Security reminders for each sensitive var

**Example:**
```bash
# .env.production.example - COPY THIS FILE AND FILL IN VALUES

# ─── REQUIRED: Change these for production ───────────────────
SECRET_KEY=<generate-with: python -c 'import secrets; print(secrets.token_urlsafe(32))'>
ANTHROPIC_API_KEY=<get-from-anthropic-dashboard>
OPENAI_API_KEY=<get-from-openai-dashboard>
COPILOT_API_KEY=<get-from-github>

# ─── Database & Vector Search ────────────────────────────────
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/samma_ai
QDRANT_HOST=qdrant-prod.internal
QDRANT_PORT=6333

# ─── Security ────────────────────────────────────────────────
CORS_ORIGINS=https://samma-ai.com
ENV=production

# ─── Observability ──────────────────────────────────────────
SENTRY_DSN=<get-from-sentry>
LOG_LEVEL=INFO
```

**Acceptance Criteria:**
- [ ] All required vars documented
- [ ] Secure defaults recommended
- [ ] No secrets hardcoded
- [ ] Clear instructions for filling in values

**Estimated Effort:** 1 hour

---

### Task 5.4: Create Runbook for Common Issues

**File:** `docs/RUNBOOK.md` (NEW)

**Content:**
- Common failure scenarios
- How to diagnose each issue
- Step-by-step resolution
- Escalation path

**Scenarios:**
1. **Qdrant unavailable** → Vector search disabled, falls back to FTS5
2. **MongoDB connection lost** → Request fails with 503
3. **LLM request timeout** → Retry or return cached response
4. **High latency** → Check query complexity, enable cache
5. **Memory leak** → Check connection pool, restart workers

**Example:**
```markdown
## Qdrant Unavailable

### Symptoms
- Health check `/health/detailed` shows vector_db=unhealthy
- Logs contain: "Cannot reach Qdrant"
- Chat responses slower than usual (keyword search fallback)

### Diagnosis
1. Check if Qdrant container is running:
   `docker ps | grep qdrant`
2. Check Qdrant logs:
   `docker logs qdrant`
3. Ping Qdrant:
   `curl http://qdrant-host:6333/health`

### Resolution
1. Restart Qdrant:
   `docker restart qdrant`
2. Wait 30s for recovery
3. Verify health check passes
4. Monitor response times for 5 minutes

### Escalation
If Qdrant remains unhealthy:
1. Check disk space: `df -h`
2. Check memory: `free -h`
3. Restore from backup if corrupted
4. Contact DevOps on #incident-channel
```

**Acceptance Criteria:**
- [ ] 5+ scenarios documented
- [ ] Clear diagnosis steps
- [ ] Actionable resolution steps
- [ ] Team trained on runbook

**Estimated Effort:** 1.5 hours

---

## Summary by Phase

| Phase | Tasks | Duration | Status | Dependencies |
|-------|-------|----------|--------|--------------|
| 1: Security | 5 | 4-6h | ⏳ Ready | None |
| 2: Config | 4 | 6-8h | ⏳ Ready | Phase 1 |
| 3: Testing | 4 | 12-16h | ⏳ Ready | Phase 1-2 |
| 4: Performance | 4 | 8-10h | ⏳ Ready | Phase 1-3 |
| 5: Documentation | 4 | 4-6h | ⏳ Ready | Phase 1-4 |
| **TOTAL** | **21** | **30-45h** | ⏳ Ready | - |

---

## Resource Allocation Recommendation

### Team Size: 3 developers

**Developer A (Security & Backend Lead):**
- Phase 1: All 5 tasks (4-6h)
- Phase 2: Tasks 2.1, 2.2 (3h)
- Total: 7-9 hours

**Developer B (Testing & QA Lead):**
- Phase 2: Tasks 2.3, 2.4 (2.5h)
- Phase 3: All 4 tasks (12-16h)
- Total: 14.5-18.5 hours

**Developer C (DevOps & Performance):**
- Phase 4: All 4 tasks (8-10h)
- Phase 5: All 4 tasks (4-6h)
- Total: 12-16 hours

**Parallel Execution:**
- Days 1-2: Dev A on Phase 1 + Dev B starting Phase 2 tasks + Dev C on initial Phase 4 setup
- Days 3-4: Dev B on Phase 3 + Dev C on Phase 4 optimization
- Days 5: Dev A on Phase 2 finalization + Dev B on coverage targets + Dev C on Phase 5
- Day 6: Final integration testing + Phase 5 documentation

**Total Timeline: 5-6 days (1 development week)**

---

## Success Criteria

### All Phases Complete When:
- [ ] All 21 tasks marked complete
- [ ] No critical security issues remain
- [ ] >80% test coverage achieved
- [ ] Performance benchmarks show improvement
- [ ] Documentation updated
- [ ] Team trained on new processes
- [ ] Code review approved by 2+ reviewers

### Ready for Production When:
- [ ] All security findings resolved
- [ ] Health checks pass (all services healthy)
- [ ] Load test passes (100+ concurrent users)
- [ ] Zero critical bugs in testing
- [ ] Deployment checklist completed
- [ ] Secrets rotated and secured
- [ ] Team on-call and trained

---

**Status:** Ready to begin Phase 1
**Next Action:** Create GitHub issues for each task in the order listed
**Review & Approval:** Team lead sign-off required before starting

---

*This plan is living documentation. Update as tasks complete and new findings emerge.*
