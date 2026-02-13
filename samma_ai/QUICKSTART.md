# Samma AI - Quick Start (5 minutes)

## Start Backend

```bash
cd samma_ai/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install & run
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-key-here"  # Set your API key
python run.py
```

You should see:
```
🧘 Samma AI Backend
Port: 5001
Endpoints:
  POST /api/chat     - Chat
  GET  /api/health   - Health
  ...
```

## Start Frontend

In a **new terminal**:

```bash
cd samma_ai/frontend

flutter pub get
flutter run -d chrome
```

Opens at: http://localhost:8080

## What You Can Do

### Chat Tab
- Ask Samma AI Dhamma questions
- Get 4-part responses with canonical sources
- Examples:
  - "What is dukkha?"
  - "Explain the Four Noble Truths"
  - "What is metta?"

### Agents Tab
- **Status**: View all 28 agents by team
- **Teams**: Chat with team leads
- **Direct**: Message individual agents
- **Tasks**: Manage task board

## Key Skills

```
/response "What is impermanence?"   # Generate response
/lookup dukkha                      # Pali word
/sutta MN 10                        # Get sutta
/team engineering                   # Message team
/status                             # Agent status
/memory-update                      # End of session
```

## Session End

Before closing:
```
/memory-update
```

This saves:
- Daily log with what you did
- Current state in CONTEXT.md
- Insights for learning

---

**Next:** Read `SETUP.md` for detailed configuration

**Need help?** Check `.claude/INIT.md`
