# 🧘 Samma AI - START HERE

## ⚡ Quick Start (2 minutes)

```bash
cd /mnt/sda1/mango1_home/pala-platform/samma_ai
bash START.sh
```

That's it! The script will:
1. Start Flask backend on http://localhost:5001
2. Start Flutter web app on http://localhost:8080
3. Open browser automatically
4. Show instructions

---

## 🌐 Once Running

### Chat Tab - Talk to Samma AI

Ask any question about Buddhism:

```
"What is dukkha?"
"Explain the Four Noble Truths"
"What is metta meditation?"
"How do I practice mindfulness?"
"What does the Buddha teach about suffering?"
```

**4-Part Response Format:**
1. **Database Summary** - What Tipitaka says
2. **Interpretive Summary** - Modern understanding
3. **Teachings** - 3-7 canonical passages with sources
4. **Final Summary** - Consolidated wisdom

### Agents Tab - Manage 28 Agents in 6 Teams

**Status View**
- See all agents by team
- Check who's available
- See current tasks

**Team Chat**
- Select a team
- Chat with team lead
- Delegate work

**Direct Message**
- Search for specific agent
- Send direct message
- Get quick responses

**Task Board**
- Pending → In Progress → Done
- Assign tasks to agents
- Track progress

---

## 🛠️ Available Skills

Use these in the chat to trigger agent actions:

| Skill | What It Does |
|-------|--------------|
| `/response "question"` | Generate 4-part Dhamma response |
| `/lookup dukkha` | Look up Pali word |
| `/sutta MN 10` | Fetch sutta by reference |
| `/team engineering` | Chat with engineering team |
| `/agent flutter-web` | Direct message agent |
| `/status` | Check agent status |
| `/optimize` | Analyze token usage |
| `/cost` | Show cost report |
| `/memory-update` | Save session to memory |

---

## 📚 What's Inside

### Backend (Flask + Claude API)
- **REST API** at http://localhost:5001
- Connects to Tipitaka database (73,765 paragraphs)
- Integrates with Claude API
- Handles 4-part response generation

### Frontend (Flutter Web)
- **Chat Interface** - Talk to Samma AI
- **Agent Dashboard** - Manage 28 agents
- **Brown + Gold Theme** - Beautiful, readable
- **Responsive Design** - Works on all devices

### Agents (28 Total)
```
Engineering Team (5)
  - flutter-web, flask-api, database-architect, integration...

Tipitaka Mastery Team (7)
  - sutta/vinaya/abhidhamma experts, pali-linguist...

Quality Assurance Team (5)
  - code-reviewer, test-runner, security-auditor...

AI/ML Team (5)
  - claude-integrator, embeddings-trainer, rag-pipeline...

DevOps Team (5)
  - docker-builder, ci-cd, monitoring...

Optimization Team (5)
  - token-optimizer, model-selector, cost-tracker...
```

### Database
- **tipitaka_ultimate.db** (1.1GB)
- 73,765 Pali passages
- 74,050 English translations
- 3,475 canonical texts indexed

---

## 🧠 Memory System

At the end of each session:

```
/memory-update
```

This saves:
- What you did today
- Current project state
- Insights and learnings

Next session, read:
- `.claude/INIT.md` - Bootstrap
- `.claude/CONTEXT.md` - Current state
- `.claude/MEMORY.md` - Long-term knowledge

---

## 🎯 Example Workflows

### Workflow 1: Learn Dhamma
1. Chat Tab
2. Ask: "What is impermanence?"
3. Get 4-part response with sources
4. Reference canonical texts

### Workflow 2: Manage Agents
1. Agents Tab → Status
2. See all 28 agents by team
3. Click on an agent for details
4. Assign a task

### Workflow 3: Team Communication
1. Agents Tab → Teams
2. Select "Engineering"
3. Send: "Create new dashboard feature"
4. Team lead responds with plan

### Workflow 4: Direct Messaging
1. Agents Tab → Direct
2. Search "flutter-web"
3. Send: "Build responsive chat widget"
4. Agent executes and reports back

---

## 🛑 When Done

Press **Ctrl+C** to stop servers

Before next session, use: `/memory-update`

---

## 📖 Full Documentation

- `QUICKSTART.md` - Quick overview
- `SETUP.md` - Detailed setup guide
- `RUN_CHECKLIST.md` - Step-by-step checklist
- `.claude/INIT.md` - Bootstrap for next session
- `docs/SOUL.md` - Complete identity & protocol

---

## 💡 Pro Tips

1. **Hot Reload** - Press 'r' in terminal while Flutter is running to reload without restart
2. **Search** - In Agents tab, search by agent name to find specific agent
3. **Keyboard** - Use Tab to navigate, Enter to send messages
4. **Multiple Chats** - Keep chat history, each message builds on previous
5. **Agent Status** - Green = active, Orange = busy, Gray = idle, Red = offline

---

## ❓ Troubleshooting

**Backend won't start:**
```bash
cd backend
source venv/bin/activate
python run.py
```

**Frontend won't open:**
```bash
cd frontend
flutter run -d chrome
```

**No database found:**
```bash
ls -lh database/tipitaka_ultimate.db
# Should show 1.1G file
```

**API key error:**
Check `backend/.env` has:
```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## 🚀 Ready?

```bash
bash START.sh
```

Then visit: **http://localhost:8080**

Enjoy! 🧘

---

*Samma AI - Dhamma-grounded AI companion for the path to liberation*
