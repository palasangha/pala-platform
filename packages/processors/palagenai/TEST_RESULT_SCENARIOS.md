# Test Result Scenarios & Decision Trees

Guide for interpreting test results and deciding on next actions.

## Scenario 1: All Metrics Excellent (Best Case)

**Results:**
- Average Completeness: 0.97+
- Auto-approval: 95%+
- Cost per document: $0.04-0.08
- All agents healthy
- No low-confidence fields

**Decision: ✅ PROCEED TO PRODUCTION**

Actions:
1. Document results in git commit
2. Create production deployment plan
3. Begin Phase 9: Production Deployment
4. No optimizations needed

Next step: See PRODUCTION_DEPLOYMENT_CHECKLIST.md

---

## Scenario 2: Good Completeness, Acceptable Costs

**Results:**
- Average Completeness: 0.92-0.95
- Auto-approval: 85-90%
- Cost per document: $0.08-0.15
- 1-2 agents with issues
- Some low-confidence fields

**Decision: ⚠️ MINOR OPTIMIZATION REQUIRED**

Actions:
1. Identify which fields are missing most
2. Focus optimization on 1-2 agents
3. Update prompts (1-2 iterations)
4. Re-test with same 5 documents
5. Target: Completeness 0.95+

Estimated effort: 2-4 hours

If completeness still <0.92 after optimization:
- Consider disabling expensive Phase 3 agent
- Move to production with human review for low-completeness docs

---

## Scenario 3: Low Completeness, High Costs

**Results:**
- Average Completeness: 0.85-0.92
- Auto-approval: 75-85%
- Cost per document: $0.20-0.50
- Multiple agents underperforming
- Many low-confidence fields

**Decision: 🔴 OPTIMIZATION REQUIRED**

Actions:
1. Disable Phase 3 (context-agent) to reduce costs
   ```bash
   ENABLE_PHASE3_CONTEXT=false
   ```
2. Re-test to see if completeness improves with cost reduction
3. If completeness improves: Continue optimization
4. If completeness still low: Review agent prompts systematically

Systematic optimization:
1. Start with entity-agent (most complex)
2. Add comprehensive name/org extraction examples
3. Test and measure improvement
4. Move to next agent if needed

Estimated effort: 4-8 hours

---

## Scenario 4: High Costs but Good Completeness

**Results:**
- Average Completeness: 0.95+
- Auto-approval: 90%+
- Cost per document: $0.40-0.60 (exceeds target)
- All agents healthy

**Decision: ⚠️ COST OPTIMIZATION NEEDED**

Root causes:
- Phase 3 (context-agent) using too many tokens
- Entity-agent making excessive Claude calls
- Prompts generating very long outputs

Solutions:
1. Disable Phase 3 if costs still acceptable:
   ```bash
   ENABLE_PHASE3_CONTEXT=false
   # Target cost: $0.04-0.08/doc
   ```
2. If still expensive, reduce token usage:
   - Shorten summaries in content-agent
   - Reduce biographical details in context-agent
   - Use Ollama more, Claude less

Re-test after each change.

Estimated effort: 1-2 hours

---

## Scenario 5: Specific Agent Failures

### metadata-agent Underperforming

**Symptoms:**
- Missing: `metadata.document_type`, `metadata.access_level`
- Low confidence: Misclassification happening

**Root cause:**
- Classification prompt too generic
- Missing edge cases

**Solutions:**
1. Add more classification examples
2. Include ambiguous cases (memo vs letter, etc.)
3. Add explicit decision rules
4. Example:
   ```
   If letter has:
     - Greeting ("Dear") → letter
     - TO: FROM: SUBJECT: → memo
     - STOP markers → telegram
   ```

Re-test and measure improvement.

---

### entity-agent Underperforming

**Symptoms:**
- Missing: `analysis.people`, `analysis.organizations`
- Relationships not extracted

**Root cause:**
- NER prompt too generic
- Missing name variation examples
- No role/affiliation extraction

**Solutions:**
1. Add diverse name examples:
   - Full names: "S.N. Goenka"
   - Titles: "Shri Desai", "Mr. Kumar"
   - Organizational: "The Vipassana Academy"
2. Add role indicators:
   - From salutation: "Dear X" → recipient
   - From closing: "Signed by X" → sender
3. Extract affiliations from context

Estimated tokens: +20-30% but better extraction

---

### structure-agent Underperforming

**Symptoms:**
- Missing: `content.salutation`, `content.closing`
- Letter parts not properly parsed

**Root cause:**
- Parsing logic too simple
- Missing variant examples

**Solutions:**
1. Add comprehensive examples:
   ```
   Salutation variants:
     - "Dear Mr. Smith,"
     - "My dear friend,"
     - "To the Dhamma Workers,"
     - "Smith," (bare name)
   ```
2. Add closing variants:
   ```
   Closing phrases:
     - "Sincerely,"
     - "With all good wishes,"
     - "In good wishes,"
     - "With blessings," + signature
   ```
3. Improve parsing logic

---

### content-agent Underperforming

**Symptoms:**
- Missing: `content.summary`
- Summaries too generic/vague
- Keywords not domain-specific

**Root cause:**
- Summary prompt lacks examples
- Keyword list too generic
- No domain context

**Solutions:**
1. Add historical letter examples:
   ```
   Example: "Invitation to meditation center opening, June 1-11, 1978"
   Instead of: "Letter about meditation practice"
   ```
2. Add domain keywords:
   ```
   Vipassana-specific: "Vipassana", "meditation", "dharma",
   "teacher training", "course", "practice", "technique"
   Generic to avoid: "letter", "the", "and", "about"
   ```
3. Add subject classification examples

---

### context-agent Underperforming

**Symptoms:**
- Missing: `analysis.historical_context`
- Generic or missing historical background
- No biographical information

**Root cause:**
- Context generation prompt vague
- No historical references provided
- Expensive to fix (uses Claude Opus)

**Solutions:**
1. **Option A**: Disable if costs exceed budget
   ```bash
   ENABLE_PHASE3_CONTEXT=false
   ```
2. **Option B**: If completeness still needed:
   - Provide more historical context in prompt
   - Use specific dates and events
   - Add biographical database references
   - Limit to top 2-3 people

May require manual historical data enrichment.

---

## Scenario 6: Specific Field Failures

### Missing Fields Analysis

Common patterns and solutions:

| Missing Field | Common Cause | Quick Fix |
|---------------|-------------|-----------|
| `metadata.id` | Not generated | Add unique ID generation |
| `metadata.document_type` | Classification weak | Add 5+ examples |
| `content.summary` | Prompt too vague | Add example summaries |
| `analysis.people` | NER weak | Add name format examples |
| `analysis.keywords` | Generic extraction | Add domain-specific list |
| `analysis.historical_context` | Expensive/unclear | Consider disabling |
| `document.correspondence` | Parsing incomplete | Add parsing examples |

---

## Scenario 7: Mixed Results (Some Docs Perfect, Others Poor)

**Results:**
- High variance in completeness (0.5 to 0.99)
- Some documents 100% complete, others <80%

**Root cause:**
- Agent performance varies by document type
- OCR quality varies significantly
- Letter structures differ

**Analysis:**
1. Group documents by:
   - OCR confidence level
   - Document type
   - Completeness score

2. Identify patterns:
   - Do high OCR confidence docs score better?
   - Do certain letter types fail?
   - Is one agent consistently weak?

3. Targeted optimization:
   - Optimize prompts for weak document types
   - Add OCR confidence handling
   - Adjust thresholds per document type

---

## Scenario 8: Unacceptable Performance

**Results:**
- Average Completeness: <80%
- Auto-approval: <70%
- Cost per document: >$1.00
- Multiple agents failing

**Decision: 🔴 REASSESS APPROACH**

Options:

**A. Extended Optimization (2-3 days)**
- Deep review of all agent prompts
- Systematic testing of variations
- Consider hiring ML engineer for help
- May not succeed

**B. Hybrid Human-AI Model (Recommended)**
- Use agents for what they do well
- Route problematic cases to human review
- Lower automatic processing rate (60-70% vs 90%)
- Higher human review rate but guaranteed quality

**C. Different Agent Strategy**
- Try different model combinations
- Use Claude for Phase 1 (more expensive but higher quality)
- Specialized prompts for each letter type

**D. Fallback to Manual Processing**
- Acknowledge full automation not viable
- Use agents for partial enrichment (40-60%)
- Manual enrichment for remainder
- Assess cost/benefit

Recommendation: Option B (Hybrid) provides best balance

---

## Decision Tree: Quick Reference

```
START: Run ./run-e2e-test.sh & ./analyze-results.sh

Is Completeness ≥ 0.95?
├─ YES → Is Cost ≤ $0.50/doc?
│         ├─ YES → ✅ PROCEED TO PRODUCTION
│         └─ NO  → ⚠️ Disable Phase 3, test again
│
└─ NO  → Is Completeness ≥ 0.92?
         ├─ YES → ⚠️ MINOR OPTIMIZATION
         │       (2-4 hours, focus on 1-2 agents)
         │
         └─ NO  → Is Cost > $0.50/doc?
                  ├─ YES → 🔴 COST OPTIMIZATION
                  │       (Disable Phase 3, re-test)
                  │
                  └─ NO  → 🔴 MAJOR OPTIMIZATION
                          (4-8 hours, systematic review)

If optimization successful → GO TO PRODUCTION
If optimization fails (3 iterations) → Hybrid Model
```

---

## Success Criteria Checklist

Before moving to production, verify:

**Phase 8 Completion:**
- [ ] Completeness ≥95% achieved
- [ ] Auto-approval ≥90% achieved
- [ ] Cost ≤$0.50/doc achieved
- [ ] All agents stable
- [ ] Measurements documented
- [ ] Changes committed to git

**Production Readiness:**
- [ ] All checklist items (see PRODUCTION_DEPLOYMENT_CHECKLIST.md)
- [ ] Infrastructure prepared
- [ ] Monitoring configured
- [ ] Backups tested
- [ ] Team trained
- [ ] Stakeholder sign-off obtained

---

## Escalation Process

If you're stuck after optimization attempts:

1. **1st attempt** (2 hours): Follow this guide
2. **2nd attempt** (4 hours): Review agent prompts systematically
3. **3rd attempt** (4 hours): Try different model combinations
4. **Escalate**:
   - Discuss with team lead
   - Consider hybrid human-AI model
   - Plan extended optimization sprint
   - or Accept current performance level

Default recommendation: **Hybrid model** balances quality and automation

