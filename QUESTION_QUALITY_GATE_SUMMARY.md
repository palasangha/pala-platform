# Question Quality Gate Implementation

## Summary
Updated question generation to filter out low-quality questions during generation time. Only questions with strong evidence (confidence >= 0.65) are retained.

## Changes Made

### 1. `setup-dev.sh` - Install Embedding Model
- Added `sentence-transformers` to the agent venv dependency installation
- Run `./setup-dev.sh` to install the embedding model

### 2. `question_generator.py` - Quality Gate Filter
- **Location**: End of `generate_questions_for_document()` after fallback logic
- **Logic**:
  - Requires evidence confidence >= 0.65 (same as fallback threshold)
  - Rejects questions with repeated, low-confidence evidence
  - Returns only "good" questions or minimal fallback (top 3) if all fail
  - Logs ACCEPT/REJECT decisions with confidence and snippet reuse counts

## Thresholds

| Parameter | Value | Reason |
|-----------|-------|--------|
| Confidence floor | 0.65 | High enough to avoid weak matches |
| Repeated snippet limit | 1 | Only 1st occurrence allowed for repeated evidence |

## Results Expected

### Before
- 10 questions generated; 4/10 verified by LLM (40% pass rate)
- Many questions with low confidence (0.5) and repeated evidence

### After
- ~4-6 questions retained per document (best evidence only)
- Confidence filtered to >= 0.65 (median 0.75+)
- No repeated evidence (except 1st occurrence)
- Expected verification pass rate: 70%+ (higher quality subset)

## How to Test

1. Run setup to install sentence-transformers:
   ```bash
   ./setup-dev.sh
   ```

2. Re-run regeneration with the updated agent:
   ```bash
   python3 packages/PalaAgents/storage-agent/batch_regenerate_questions.py \
     --limit 5 --verify
   ```

3. Check logs for `[QUALITY-GATE] ACCEPT/REJECT` lines to see filtering in action

## Configuration

To adjust quality thresholds, edit `question_generator.py`:
- Line ~610 (quality gate): Change `conf >= 0.65` to your target threshold
- Line ~612: Change `repeated_count <= 1` to allow more repeated evidence

## Trade-offs

**Pros:**
- Fewer but higher-quality questions
- Reduced false positives in search
- Faster verification (fewer LLM calls)

**Cons:**
- May return 0 questions if document has weak keyword matches
- Fallback of top 3 ensures at least some output (tunable)

## Next Steps

1. Install and run setup-dev.sh
2. Test regeneration on a small batch
3. Compare verification pass rates (before: 4/10, after: ?/X)
4. Adjust confidence threshold if needed (default 0.65 is recommended)
