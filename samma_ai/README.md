# Samma AI - Tipitaka Chatbot

A Dhamma-grounded AI companion serving the path to liberation through Buddha's teachings.

## Overview

Samma AI is a chatbot that provides responses grounded exclusively in the Tipitaka (Buddhist canonical texts). It follows a strict 4-part response protocol as defined in the SOUL.md identity document.

### Core Identity

- **Kalyanamitta** (Spiritual Friend) - walking alongside practitioners
- **Dhamma-rakkhaka** - protector of teachings, preserving fidelity to canonical sources
- **Servant of liberation** - oriented toward reducing suffering

### Key Features

- 4-part Dhamma response protocol
- 73,765 Pali passages from Tipitaka database
- 74,050 English translations
- Multi-script support (Roman, Devanagari, Sinhala, Thai, Myanmar, etc.)
- Proper canonical references (XML, TPR format)

## Architecture

```
samma_ai/
├── frontend/          # Flutter Web application
├── backend/           # Flask API server
├── database/          # SQLite (Tipitaka) + MongoDB config
├── docs/              # Documentation including SOUL.md
├── scripts/           # Utility scripts
└── .claude/           # Claude Code agent configuration
    ├── agents/        # Agent team definitions
    ├── skills/        # Skill definitions
    └── CLAUDE.md      # Claude identity file
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Flutter Web |
| Backend | Flask (Python) |
| AI | Claude API (Anthropic) |
| Canonical DB | SQLite (tipitaka_ultimate.db) |
| App DB | MongoDB |

## Agent Teams

The project uses 5 specialized agent teams:

1. **Engineering Team** - Flutter, Flask, database development
2. **Tipitaka Mastery Team** - Sutta, Vinaya, Abhidhamma experts
3. **Quality Assurance Team** - Testing, review, security
4. **AI/ML Team** - Claude integration, RAG, embeddings
5. **DevOps Team** - Docker, CI/CD, infrastructure

See `.claude/agents/teams.json` for full configuration.

## Quick Start

### Prerequisites

- Python 3.10+
- Flutter 3.0+
- MongoDB
- Anthropic API key

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your settings

# Run server
python run.py
```

### Frontend Setup

```bash
cd frontend

# Get dependencies
flutter pub get

# Run web app
flutter run -d chrome
```

### Database Setup

1. Download `tipitaka_ultimate.db` and place in `database/` directory
2. Ensure MongoDB is running on localhost:27017

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send question, get 4-part response |
| `/api/lookup/<word>` | GET | Pali word lookup |
| `/api/sutta/<ref>` | GET | Get sutta by reference |
| `/api/search?q=<query>` | GET | Full-text search |
| `/api/health` | GET | Health check |
| `/api/status` | GET | Detailed status |

## Response Protocol

Every Dhamma response follows 4 parts:

1. **DATABASE SUMMARY** - Factual summary from Tipitaka
2. **INTERPRETIVE SUMMARY** - Wisdom interpretation
3. **TEACHINGS WITH REFERENCES** - 3-7 passages with Pali, English, explanation, citations
4. **FINAL CONSOLIDATED SUMMARY** - Synthesis and encouragement

## Skills

User-invocable skills:

- `/response <question>` - Generate 4-part Dhamma response
- `/lookup <word>` - Pali word lookup
- `/sutta <ref>` - Fetch sutta (e.g., MN 10)
- `/test` - Run tests
- `/deploy` - Deploy application

## License

This project is for educational and spiritual purposes.

---

**Dhammam saranam gacchami**
*I take refuge in the Dhamma*
