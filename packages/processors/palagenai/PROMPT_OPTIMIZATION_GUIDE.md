# Prompt Optimization Guide

Guide for analyzing test results and refining MCP agent prompts to improve enrichment completeness and accuracy.

## Overview

After running the E2E test suite (`./run-e2e-test.sh`), use this guide to:
1. **Analyze** results from `analyze-results.sh`
2. **Identify** failing fields and low-confidence outputs
3. **Refine** prompts in each agent
4. **Re-test** to measure improvements

## Phase 1: Analyze Test Results

### Step 1: Run E2E Test

```bash
./run-e2e-test.sh
# Output: analyze-results.sh report
```

### Step 2: Extract Key Metrics

From the analysis report, identify:

```
Completeness Analysis:
  Average Completeness: X.XXX (target: ≥0.95)
  Median Completeness: X.XXX
  Distribution: [how many docs in each % range]

Missing Fields Analysis:
  - field_path: count (% of docs)  ← Focus on top 5
```

**Example problematic output:**
```
Missing Fields Analysis:
  analysis.historical_context: 4 docs (80%)  ← CRITICAL
  analysis.significance: 3 docs (60%)        ← HIGH
  content.summary: 1 doc (20%)               ← MEDIUM
  analysis.keywords: 0 docs (0%)             ← GOOD
```

### Step 3: Check Cost Metrics

```
Cost by Model:
  ollama: $0.00 (Phase 1 - free)
  claude-sonnet-4: $0.045 (Phase 2)
  claude-opus-4-5: $0.XXX (Phase 3)
```

If Phase 3 cost is too high, disable it in `.env`:
```bash
ENABLE_PHASE3_CONTEXT=false
```

## Phase 2: Identify Root Causes

### Common Issues & Solutions

| Symptom | Root Cause | Solution |
|---------|-----------|----------|
| Missing `analysis.historical_context` | context-agent prompt unclear | Refine history prompt with examples |
| Missing `content.summary` | content-agent doesn't understand structure | Add letter format examples |
| Missing `analysis.people` | entity-agent not extracting names | Improve NER prompt, add name patterns |
| Low `analysis.keywords` confidence | Too generic keyword extraction | Add domain-specific keyword list |
| Missing `document.correspondence` | structure-agent parser weak | Add salutation/closing examples |
| Low `metadata.access_level` confidence | Unclear sensitivity indicators | Define sensitivity rules |

## Phase 3: Prompt Refinement Workflow

### Step 1: Identify Top 3 Problem Fields

From analysis, identify fields missing in most documents:

```bash
# Example from analyze-results.sh output
analysis.historical_context: 4/5 docs (80% missing)  ← #1
analysis.people: 3/5 docs (60% missing)              ← #2
content.summary: 2/5 docs (40% missing)              ← #3
```

### Step 2: Refine Prompts

For each field, edit the corresponding agent prompt:

**Field → Agent Mapping:**
- `metadata.*` → metadata-agent
- `analysis.people`, `analysis.organizations` → entity-agent
- `content.salutation`, `content.closing` → structure-agent
- `content.summary`, `analysis.keywords` → content-agent
- `analysis.historical_context`, `analysis.significance` → context-agent

### Step 3: Test Refinements

```bash
# Re-run test with same 5 documents
./test-data/insert-test-data.sh
./run-e2e-test.sh --skip-deploy

# Compare results
./analyze-results.sh

# Check improvement in completeness
# Look for reduced missing fields count
```

### Step 4: Measure Improvement

Track metrics before and after:

```
BEFORE refinement:
  Average Completeness: 0.90
  Missing fields (top 3): analysis.historical_context (4), analysis.people (3)
  Cost per doc: $0.15

AFTER refinement:
  Average Completeness: 0.95 ✓
  Missing fields (top 3): analysis.historical_context (1), analysis.people (1)
  Cost per doc: $0.15 (no change)
```

## General Prompt Guidelines

✅ **Good prompt characteristics**:
- Clear task description
- Specific output format (JSON)
- Multiple relevant examples
- Edge cases addressed
- Confidence scoring requested
- Constraints explicitly stated

❌ **Avoid**:
- Vague instructions
- Unstructured output
- No examples
- Missing constraints

## Agent-Specific Refinement Strategy

### metadata-agent: Document Classification

**Focus**: Classify document type correctly

```
Missing metadata.document_type → Add more classification examples
Missing metadata.access_level → Define sensitivity rules
Low confidence → Add edge cases
```

**Improvement approach**:
- Add examples of each type: letter, memo, telegram, invitation, certification
- Include ambiguous cases (e.g., memo that looks like letter)
- Define access rules (e.g., "personal" = restricted, "official" = public)

### entity-agent: Entity Extraction

**Focus**: Extract people and organizations

```
Missing analysis.people → Not all names extracted
Missing analysis.organizations → Org names not recognized
Low confidence → Ambiguous references
```

**Improvement approach**:
- Add examples of name variations (titles, nicknames, formal names)
- Include role indicators (sender, recipient, mentioned)
- Add organizational context extraction

### structure-agent: Letter Structure

**Focus**: Parse letter components

```
Missing content.salutation → Salutation not identified
Missing content.closing → Closing not identified
Missing document.correspondence → Metadata not extracted
```

**Improvement approach**:
- Add variant salutation examples ("Dear", "My dear", "To", bare names)
- Add closing examples ("Sincerely", "With wishes", signatures)
- Extract sender/recipient from salutation and closing

### content-agent: Content Generation

**Focus**: Generate summaries and keywords

```
Missing content.summary → Summary generation failed
Low analysis.keywords confidence → Generic keywords
Missing analysis.subjects → Subject classification unclear
```

**Improvement approach**:
- Add domain-specific examples for Vipassana/meditation letters
- Include historical event context
- Specify keyword quality criteria (specific, searchable, in text)

### context-agent: Historical Context

**Focus**: Add historical enrichment

```
Missing analysis.historical_context → Context not generated
Missing analysis.significance → Significance not assessed
Low biography quality → Incomplete biographical information
```

**Improvement approach**:
- Add historical background context (specific dates, events, movements)
- Define what "significant" means (impact, influence, historical record)
- Require biographical details for each person

## Testing After Optimization

### Before Making Changes

Run baseline test:
```bash
./run-e2e-test.sh
./analyze-results.sh > baseline_results.txt
```

Record these metrics:
- Average completeness
- Missing fields (top 10)
- Cost per document
- Low confidence fields

### Make Prompt Changes

Edit agent prompts in:
- `packages/agents/metadata-agent/tools/prompts.py`
- `packages/agents/entity-agent/tools/prompts.py`
- `packages/agents/structure-agent/tools/prompts.py`
- `packages/agents/content-agent/tools/prompts.py`
- `packages/agents/context-agent/tools/prompts.py`

### After Making Changes

Re-run test with same data:
```bash
# Clear old results
docker-compose -f docker-compose.enrichment.yml down -v

# Re-deploy and test
./run-e2e-test.sh
./analyze-results.sh > optimized_results.txt
```

### Compare Results

```bash
# Compare completeness
grep "Average Completeness" baseline_results.txt optimized_results.txt

# Compare missing fields
grep "Missing Fields Analysis" -A 5 baseline_results.txt optimized_results.txt

# Look for improvements
diff baseline_results.txt optimized_results.txt
```

## Optimization Success Criteria

Stop optimizing when you achieve:

| Metric | Target | Status |
|--------|--------|--------|
| Average Completeness | ≥0.95 | ✓ |
| Auto-Approval Rate | ≥90% | ✓ |
| Cost per Document | ≤$0.50 | ✓ |
| Median Completeness | ≥0.95 | ✓ |
| Perfect Completeness | ≥60% | ✓ |
| Low Confidence Fields | <5% docs | ✓ |

When all criteria met, proceed to production deployment.

## Common Optimization Mistakes

1. **Changing multiple prompts at once** - Can't measure which change worked
2. **Over-optimizing for test data** - May not generalize to production
3. **Ignoring cost impact** - Some refinements may increase costs
4. **Not measuring baseline** - Can't assess improvement without before/after
5. **Giving up too early** - 2-3 iterations usually needed
6. **Over-specifying prompts** - Too many rules confuse the model
7. **Ignoring confidence scores** - May indicate uncertain extraction

## Iterative Refinement Process

```
Round 1:
  Run E2E test → Analyze results → Identify issues

Round 2:
  Refine top-3 agents → Re-test → Compare metrics

Round 3:
  Fine-tune remaining agents → Re-test → Compare metrics

Round 4 (if needed):
  Optimize costly operations → Re-test → Verify cost/quality trade-off

SUCCESS:
  All metrics meet targets → Ready for production
```

## Documentation for Changes

After successful optimization, document what changed:

```bash
git log -1 --oneline
# e.g., "Optimize entity-agent for better people extraction"

# In commit message:
# - Identified issue: 60% docs missing analysis.people
# - Root cause: Prompt too generic, missing name variations
# - Solution: Added 5 name format examples, role indicators
# - Result: Completeness improved 0.90 → 0.95
# - Cost impact: No change ($0.04/doc)
```

## Next Steps After Optimization

Once optimization complete (Phase 8):
1. ✅ Completeness ≥95%
2. ✅ Auto-approval ≥90%
3. ✅ Cost ≤$0.50/doc

Proceed to Phase 9: Production Deployment
- Configure SSL/TLS
- Set up backups
- Deploy monitoring
- Validate with larger batch

