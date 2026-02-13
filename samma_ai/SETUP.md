# Samma AI - Setup Guide

**Status:** Database configured ✅ | API Key ready ✅ | Ready to run

---

## Prerequisites Checklist

- [x] Database: `tipitaka_ultimate.db` (1.1GB, 73,765 paragraphs)
- [x] Backend `.env` configured
- [ ] Anthropic API key in environment
- [ ] MongoDB running (for user data)
- [ ] Python 3.10+
- [ ] Flutter 3.0+

---

## Backend Setup

### 1. Install Dependencies

```bash
cd samma_ai/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Set Anthropic API Key

```bash
# Option A: Export as environment variable
export ANTHROPIC_API_KEY="sk-ant-..."

# Option B: Add to .env file (NOT recommended for production)
# Edit backend/.env and add your key
```

### 3. MongoDB Setup (Optional but Recommended)

```bash
# If you have MongoDB installed locally
mongod

# Or use MongoDB Atlas (cloud)
# Update MONGO_URI in .env
```

### 4. Run Backend

```bash
cd samma_ai/backend
python run.py

# You should see:
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🧘 Samma AI Backend
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Environment: development
# Port: 5001
# ...
```

---

## Frontend Setup

### 1. Get Dependencies

```bash
cd samma_ai/frontend
flutter pub get
```

### 2. Run Web App

```bash
# Option A: Chrome
flutter run -d chrome

# Option B: Web server
flutter build web
cd build/web
python3 -m http.server 8080
```

Access at: http://localhost:8080

---

## API Endpoints (Backend Running)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Health check |
| `/api/status` | GET | Detailed status |
| `/api/chat` | POST | Chat with Samma AI |
| `/api/lookup/<word>` | GET | Pali word lookup |
| `/api/search?q=<query>` | GET | Full-text search |

### Test with curl

```bash
# Health check
curl http://localhost:5001/api/health

# Detailed status
curl http://localhost:5001/api/status

# Chat (requires API key)
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is dukkha?"}'
```

---

## Architecture Overview

```
User Browser (http://localhost:8080)
       ↓
   Flutter Web UI
       ↓
   REST API (http://localhost:5001)
       ↓
   Flask Backend
   ├─ Tipitaka Database (SQLite)
   ├─ MongoDB (sessions, chat history)
   └─ Claude API (responses)
```

---

## Agent Dashboard

Once running, navigate to http://localhost:8080:

1. **Chat Tab** - Talk to Samma AI
2. **Agents Tab** - View agent dashboard:
   - **Status** - All 28 agents by team
   - **Teams** - Chat with team leads
   - **Direct** - Message individual agents
   - **Tasks** - Kanban task board

---

## Memory System

At the end of each development session:

```bash
# Use the skill to update memory
/memory-update
```

This will:
- Create daily log in `.claude/memory/daily/`
- Update `.claude/CONTEXT.md`
- Flag insights for consolidation

---

## Agent Teams Available

| Team | Lead | Sub-Agents |
|------|------|-----------|
| Engineering | engineering-lead | flutter-web, flask-api, database-architect, integration |
| Tipitaka | tipitaka-lead | sutta/vinaya/abhidhamma experts, pali-linguist, reference-formatter |
| QA | qa-lead | code-reviewer, test-runner, security-auditor, performance |
| AI/ML | ai-lead | claude-integrator, embeddings-trainer, rag-pipeline, output-validator |
| DevOps | devops-lead | docker-builder, ci-cd, infra, monitoring |
| Optimization | optimization-lead | token-optimizer, model-selector, context-manager, cost-tracker |

---

## Key Skills

```
/response <question>    # Generate 4-part Dhamma response
/lookup <word>         # Pali word lookup
/sutta <ref>           # Get sutta (e.g., MN 10)
/memory-update         # Update memory at session end
/team <name>           # Message a team
/agent <name>          # Direct message an agent
/status                # Check agent status
/optimize              # Analyze token usage
/cost                  # Show cost report
```

---

## Troubleshooting

### Database Not Found
```
Error: No such table: paragraphs
```
✅ Solution: Ensure `tipitaka_ultimate.db` is in `database/` directory

### Claude API Error
```
Error: ANTHROPIC_API_KEY not configured
```
✅ Solution: Export API key:
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

### MongoDB Not Running
```
Error: Connection refused to localhost:27017
```
✅ Solution: Either start MongoDB or disable user features (comments disabled in code)

### Flutter Port Conflict
```
Error: Port 8080 already in use
```
✅ Solution: Use different port:
```bash
flutter run -d chrome --dart-define=PORT=8081
```

---

## Next Steps

1. ✅ Start backend (`python run.py`)
2. ✅ Start frontend (`flutter run -d chrome`)
3. ✅ Navigate to http://localhost:8080
4. ✅ Chat with Samma AI or explore Agent Dashboard
5. ✅ Use `/memory-update` before ending sessions

---

## File Locations

| File | Purpose |
|------|---------|
| `database/tipitaka_ultimate.db` | Canonical texts |
| `backend/.env` | Configuration |
| `backend/run.py` | Start Flask server |
| `frontend/lib/main.dart` | Flutter entry point |
| `.claude/INIT.md` | Bootstrap instructions |
| `.claude/CONTEXT.md` | Current state |
| `.claude/MEMORY.md` | Long-term knowledge |

---

## Support

- **Architecture questions** → Check `docs/SOUL.md`
- **Agent questions** → Check `.claude/agents/teams.json`
- **Memory & context** → Check `.claude/INIT.md`
- **API docs** → Check backend route files in `backend/app/routes/`

---

*Last Updated: 2026-02-09*
*Status: Ready for Development*
