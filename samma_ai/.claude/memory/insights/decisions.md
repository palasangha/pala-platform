# Decision Log

**Purpose:** Record significant decisions with rationale

---

## Architecture Decisions

### ADR-001: Flutter Web + Flask Backend
**Date:** 2026-02-09
**Status:** Accepted

**Context:**
Need a web-first chatbot with Python backend for AI integration.

**Decision:**
Use Flutter Web for frontend, Flask for backend.

**Rationale:**
- Flutter: Cross-platform potential, good web support
- Flask: Lightweight, good for AI/ML integrations
- Python ecosystem for Claude SDK, embeddings

**Consequences:**
- Need to handle Flutter web limitations
- Python backend familiar for AI work

---

### ADR-002: Claude API over Local LLM
**Date:** 2026-02-09
**Status:** Accepted

**Context:**
Need high-quality responses for Dhamma content.

**Decision:**
Use Claude API instead of local Ollama.

**Rationale:**
- Higher quality responses for nuanced spiritual content
- Better understanding of Pali terms
- Consistent quality

**Consequences:**
- API costs
- Internet dependency
- Need API key management

---

### ADR-003: Dual Database (SQLite + MongoDB)
**Date:** 2026-02-09
**Status:** Accepted

**Context:**
Need canonical Tipitaka data + app data storage.

**Decision:**
SQLite for Tipitaka (existing 1.1GB DB), MongoDB for app data.

**Rationale:**
- Tipitaka DB already exists in SQLite
- MongoDB flexible for user data, sessions, chat history

**Consequences:**
- Two database systems to manage
- Need connection pooling for both

---

### ADR-004: 6 Agent Teams Structure
**Date:** 2026-02-09
**Status:** Accepted

**Context:**
Need organized agent structure for complex project.

**Decision:**
6 teams: Engineering, Tipitaka, QA, AI/ML, DevOps, Optimization

**Rationale:**
- Clear separation of concerns
- Optimization team for token/cost management
- Scalable structure

**Consequences:**
- Need agent coordination
- Dashboard for visibility

---

### ADR-005: Skill-based Memory Updates
**Date:** 2026-02-09
**Status:** Accepted

**Context:**
Need to persist context across sessions.

**Decision:**
Use `/memory-update` skill for explicit memory updates.

**Rationale:**
- Explicit control over what gets saved
- User triggers updates at natural breakpoints
- Avoid accidental overwrites

**Consequences:**
- Requires discipline to remember
- Skill must be robust

---

## Template

### ADR-XXX: [Title]
**Date:** YYYY-MM-DD
**Status:** Proposed | Accepted | Deprecated | Superseded

**Context:**
[What is the issue that we're seeing that is motivating this decision?]

**Decision:**
[What is the change that we're proposing/making?]

**Rationale:**
[Why is this the best choice?]

**Consequences:**
[What becomes easier or harder?]

---

*Add new decisions as they are made*
