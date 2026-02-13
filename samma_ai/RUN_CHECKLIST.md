# Samma AI - Run Checklist

## Before Starting

- [ ] Have your Anthropic API key ready
- [ ] MongoDB running (optional, app works without it)
- [ ] Two terminal windows available

---

## Backend Setup & Run

### Terminal 1: Backend

```bash
# Navigate to backend
cd /mnt/sda1/mango1_home/pala-platform/samma_ai/backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set your API key (replace with actual key)
export ANTHROPIC_API_KEY="sk-ant-v7-xxxxx"

# Run the server
python run.py
```

**Expected output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧘 Samma AI Backend
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Environment: development
Port: 5001
Debug: True

Endpoints:
  POST /api/chat     - Chat with Samma AI
  GET  /api/lookup   - Pali word lookup
  GET  /api/search   - Full-text search
  GET  /api/health   - Health check
  GET  /api/status   - Detailed status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

✅ When you see this, backend is ready!

---

## Frontend Setup & Run

### Terminal 2: Frontend

```bash
# Navigate to frontend
cd /mnt/sda1/mango1_home/pala-platform/samma_ai/frontend

# Get dependencies
flutter pub get

# Run on Chrome
flutter run -d chrome
```

**Expected output:**
```
Launching lib/main.dart on Chrome in debug mode...
Building for web...
...
Running with sound null safety

🔥  To hot reload changes while running, press "r". To hot restart (and rebuild state), press "R".
For a pid to attach DevTools to, visit http://localhost:8081
The web app is running at:
  http://localhost:8080
```

✅ Browser opens automatically to http://localhost:8080

---

## Testing the Setup

### Health Check (in a 3rd terminal)

```bash
# Test backend is running
curl http://localhost:5001/api/health

# Should return:
# {"status":"healthy","service":"samma-ai-backend"}
```

### In the Web App

1. **Chat Tab**
   - Type: "What is dukkha?"
   - Press Send
   - Wait for response (10-30 seconds for first request)

2. **Agents Tab**
   - See all 28 agents by team
   - Click on an agent to view details
   - Try team chat or direct messaging

---

## Troubleshooting

### Backend Won't Start

**Error:** `ModuleNotFoundError: No module named 'anthropic'`
```bash
# Solution: Ensure virtual environment is activated
source venv/bin/activate
pip install -r requirements.txt
```

**Error:** `ANTHROPIC_API_KEY not configured`
```bash
# Solution: Set the API key first
export ANTHROPIC_API_KEY="your-key-here"
python run.py
```

**Error:** `Database file not found`
```bash
# Solution: Database should be at backend/../database/tipitaka_ultimate.db
ls -lh database/tipitaka_ultimate.db
```

### Frontend Won't Open

**Error:** `Flutter not found`
```bash
# Solution: Install Flutter or add to PATH
flutter --version
```

**Error:** `Port 8080 already in use`
```bash
# Solution: Use different port
flutter run -d chrome --web-port 8081
```

### No Response from Chat

**Error:** Takes >1 minute or no response
```bash
# Check if backend is running:
curl http://localhost:5001/api/health

# If connection refused:
# 1. Backend not started
# 2. Port 5001 blocked
# 3. API key not set
```

---

## Normal Workflow

### Session Start

1. **Read context** - Check what was done before
   ```bash
   cat .claude/INIT.md
   cat .claude/CONTEXT.md
   ```

2. **Start backend** - Terminal 1
   ```bash
   cd backend
   source venv/bin/activate
   export ANTHROPIC_API_KEY="sk-ant-..."
   python run.py
   ```

3. **Start frontend** - Terminal 2
   ```bash
   cd frontend
   flutter run -d chrome
   ```

4. **Work** - Use the app, chat, explore agents

### Session End

1. **Use memory update** - In web app
   ```
   /memory-update
   ```

2. **Stop servers** - Press Ctrl+C in both terminals

3. **Next time** - Read context files again

---

## Key Shortcuts

| Keyboard | Action |
|----------|--------|
| `Ctrl+C` | Stop server |
| `r` | Hot reload (frontend) |
| `R` | Hot restart (frontend) |
| `F5` | Refresh web page |
| `Ctrl+Shift+I` | Developer tools (browser) |

---

## File Locations

- Backend: `/mnt/sda1/mango1_home/pala-platform/samma_ai/backend/`
- Frontend: `/mnt/sda1/mango1_home/pala-platform/samma_ai/frontend/`
- Database: `/mnt/sda1/mango1_home/pala-platform/samma_ai/database/`
- Config: `/mnt/sda1/mango1_home/pala-platform/samma_ai/.claude/`

---

## Success Checklist

- [ ] Backend running on port 5001
- [ ] Frontend running on port 8080
- [ ] Browser opens automatically
- [ ] Can type in chat
- [ ] Can see Agent Dashboard
- [ ] `/memory-update` works
- [ ] Database verified with 73,765 paragraphs

---

**Ready to start?** Follow the steps above!

Need help? Check `SETUP.md` or `docs/SOUL.md`
