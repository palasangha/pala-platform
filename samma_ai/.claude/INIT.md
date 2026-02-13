# Samma AI - Session Bootstrap

**READ THIS FIRST** - This file bootstraps your context for working on this project.

---

## Quick Start Checklist

When starting a new session, read these files in order:

1. **This file** (`INIT.md`) - Bootstrap instructions
2. **`CONTEXT.md`** - Current project state, active tasks, blockers
3. **`MEMORY.md`** - Consolidated knowledge and patterns
4. **`memory/daily/[latest].md`** - Most recent session log (if exists)

---

## Project Overview

**Project:** Samma AI - Tipitaka Chatbot
**Purpose:** Dhamma-grounded AI companion for Buddhist teachings
**Stack:** Flutter Web + Flask + MongoDB + SQLite + Claude API

### Directory Structure

```
samma_ai/
├── .claude/                    # Claude Code configuration
│   ├── INIT.md                # THIS FILE - read first
│   ├── CONTEXT.md             # Current state snapshot
│   ├── CLAUDE.md              # Identity & instructions
│   ├── agents/teams.json      # 6 agent teams
│   ├── skills/skills.json     # User-invocable skills
│   ├── memory/
│   │   ├── MEMORY.md          # Long-term consolidated knowledge
│   │   ├── daily/             # Daily session logs
│   │   └── insights/          # Categorized learnings
│   └── comms/                 # Inter-agent communication
├── backend/                   # Flask API (Python)
├── frontend/                  # Flutter Web (Dart)
├── database/                  # SQLite + MongoDB configs
├── docs/                      # Documentation
│   └── SOUL.md               # Core identity & 4-part protocol
└── README.md
```

---

## Agent Teams

| Team | Lead | Purpose |
|------|------|---------|
| **Engineering** | engineering-lead | Flutter, Flask, database development |
| **Tipitaka Mastery** | tipitaka-lead | Sutta, Vinaya, Abhidhamma expertise |
| **Quality Assurance** | qa-lead | Testing, review, security |
| **AI/ML** | ai-lead | Claude integration, RAG, embeddings |
| **DevOps** | devops-lead | Docker, CI/CD, infrastructure |
| **Optimization** | optimization-lead | Token efficiency, model selection, costs |

---

## Key Protocols

### 4-Part Dhamma Response (from SOUL.md)

Every Dhamma question must have:
1. **DATABASE SUMMARY** - Facts from Tipitaka
2. **INTERPRETIVE SUMMARY** - Wisdom interpretation
3. **TEACHINGS WITH REFERENCES** - 3-7 passages with Pali, English, citations
4. **FINAL SUMMARY** - Consolidated wisdom

### Memory Update Protocol

At session end, use `/memory-update` skill to:
1. Create daily log in `memory/daily/YYYY-MM-DD.md`
2. Update `CONTEXT.md` with current state
3. Flag insights for consolidation into `MEMORY.md`

---

## Session Workflow

```
┌─────────────────────────────────────────────┐
│ SESSION START                               │
├─────────────────────────────────────────────┤
│ 1. Read INIT.md (this file)                 │
│ 2. Read CONTEXT.md (current state)          │
│ 3. Read MEMORY.md (consolidated knowledge)  │
│ 4. Check latest daily log                   │
│ 5. Resume from where we left off            │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ DURING SESSION                              │
├─────────────────────────────────────────────┤
│ • Work on tasks                             │
│ • Log significant decisions                 │
│ • Note patterns and insights                │
│ • Update CONTEXT.md if major state change   │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ SESSION END                                 │
├─────────────────────────────────────────────┤
│ Use /memory-update to:                      │
│ 1. Write daily log                          │
│ 2. Update CONTEXT.md                        │
│ 3. Flag insights for MEMORY.md              │
└─────────────────────────────────────────────┘
```

---

## Critical Files Reference

| File | Purpose | When to Update |
|------|---------|----------------|
| `docs/SOUL.md` | Core identity, 4-part protocol | Rarely |
| `CLAUDE.md` | Claude instructions | When behavior changes |
| `CONTEXT.md` | Current state snapshot | Every session |
| `MEMORY.md` | Consolidated knowledge | Weekly |
| `agents/teams.json` | Agent definitions | When adding/modifying agents |
| `skills/skills.json` | Skill definitions | When adding/modifying skills |

---

## Commands Quick Reference

| Skill | Purpose |
|-------|---------|
| `/memory-update` | Update memory at session end |
| `/context` | Show current project context |
| `/team <name>` | Interact with a team |
| `/agent <name>` | Interact with specific agent |
| `/status` | Show agent/team status |
| `/response` | Generate 4-part Dhamma response |
| `/test` | Run tests |
| `/deploy` | Deploy application |

---

## Remember

- **ALL Dhamma content** must come from the Tipitaka database
- **Prioritize accuracy** over pleasantness
- **Serve liberation**, not engagement
- **Document decisions** for future sessions
- **Update memory** before ending sessions

---

*Last updated: 2026-02-09*
