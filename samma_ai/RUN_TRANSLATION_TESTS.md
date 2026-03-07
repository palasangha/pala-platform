# Quick Start: Run Samma AI Translation Tests

## 1. Prerequisites Checklist

```bash
# Check Qdrant is running
curl -s http://localhost:6333/health && echo "✓ Qdrant OK" || echo "✗ Qdrant DOWN"

# Check Ollama is running
curl -s http://localhost:11434/api/tags && echo "✓ Ollama OK" || echo "✗ Ollama DOWN"

# Check database exists
ls -lh backend/database/tipitaka_ultimate.db | awk '{print "✓ SQLite:", $5}' || echo "✗ SQLite missing"

# Check venv
test -d backend/venv && echo "✓ venv exists" || echo "✗ venv missing"
```

## 2. Install Playwright (One-Time)

```bash
npm install @playwright/test
```

## 3. Run All Tests

```bash
npx playwright test e2e/translation.spec.ts --reporter=list
```

## 4. Run with HTML Report

```bash
npx playwright test e2e/translation.spec.ts --reporter=html
npx playwright show-report test-results/html
```

## 5. Run Specific Test

```bash
# Single test
npx playwright test -g "should translate samadhi"

# All quality validation tests
npx playwright test -g "Translation Quality Validation"

# All core translation tests
npx playwright test -g "Pali Translation Feature"
```

## 6. Troubleshooting

### Tests timeout or won't start
```bash
# Kill any existing processes
pkill -9 -f "python3 run.py"

# Try again (Playwright will auto-start backend)
npx playwright test e2e/translation.spec.ts
```

### 404 errors on `/api/chat`
```bash
# Check backend health endpoint
curl http://localhost:5001/api/health

# If it fails, backend isn't running. Check logs:
tail -50 /tmp/backend.log
```

### Ollama/Deepseek not found
```bash
# Verify Ollama is running and has deepseek loaded
curl http://localhost:11434/api/tags

# If deepseek not listed, pull it:
ollama pull deepseek-r1:32b
```

### Qdrant unhealthy
```bash
# Restart container
docker restart gvpocr-qdrant
sleep 5

# Verify
curl http://localhost:6333/health
```

## 7. Expected Results

### When Everything Works (18/18 passing)
```
✓ [chromium] › e2e/translation.spec.ts:19:7 › should translate samadhi correctly
✓ [chromium] › e2e/translation.spec.ts:52:7 › should translate metta correctly
✓ [chromium] › e2e/translation.spec.ts:82:7 › should track translation source (db vs ollama)
✓ [chromium] › e2e/translation.spec.ts:110:7 › should cache translations...
... (14 more passing)

18 passed (15s)
```

### Common Partial Failure (Some Ollama timeouts)
- Passages have `english_text` for some items
- `translation_source` is mix of 'db' and 'ollama'
- Cache performance visible on second requests
- **Fix:** Increase timeout in .env

### All Ollama Unavailable (Graceful Degradation)
- All passages have `translation_source: 'none'` or 'db'
- Tests still pass (fallback to database English text)
- No translation enrichment, but system works
- **Fix:** Start Ollama: `ollama serve`

## 8. Test Output Files

After running tests:
```
test-results/html/              ← HTML report (open in browser)
test-results/results.json       ← JSON results (parse in CI/CD)
test-results/junit.xml          ← JUnit format (Jenkins integration)
```

View HTML report:
```bash
npx playwright show-report test-results/html
```

## 9. Debug Mode (Very Verbose)

```bash
npx playwright test e2e/translation.spec.ts --debug
```

This opens the Playwright Inspector and pauses at each step.

## 10. One-Liner: Full Test + Report

```bash
npx playwright test e2e/translation.spec.ts --reporter=html && npx playwright show-report test-results/html
```

---

## What The Tests Check

### Translation Quality (Tests 1-6, 13-18)
- Pali terms translated to correct English concepts
- `samadhi` → concentration / meditative absorption
- `metta` → loving-kindness / benevolence
- `dukkha` → suffering / unsatisfactoriness
- `anicca` → impermanence / transience

### Integration (Tests 3, 7-12)
- `translation_source` field present and valid ('db' or 'ollama')
- Cache performance (second call faster than first)
- Health endpoint reports translation service status
- Response structure complete
- Multiple passages handled correctly

### Performance (Test 4, 11)
- First translation request measured
- Second request (cached) measured
- Time difference quantified
- Cache warming with multiple terms

---

## Status Summary

| Component | Status |
|-----------|--------|
| Backend init fixes | ✅ Applied |
| Playwright config | ✅ Updated |
| Test suite | ✅ 18 tests ready |
| Documentation | ✅ Complete |
| Ready to run | ✅ **YES** |

---

## Next Steps

1. Run: `npx playwright test e2e/translation.spec.ts --reporter=html`
2. View: `npx playwright show-report test-results/html`
3. Check results and share findings

**Estimated run time:** 10-15 minutes (depending on Ollama warmup)
