# GVPOCR Setup Guide

## Quick Start (Automated Setup)

For a fresh clone of the repository, use the provided setup script:

```bash
# Clone the repository
git clone https://github.com/palasangha/OCR_metadata_extraction.git
cd OCR_metadata_extraction

# Run the setup script (Linux/Mac)
./setup.sh

# On Windows, you may need to use:
# bash setup.sh
```

The setup script will:
1. Create a Python virtual environment
2. Install all backend dependencies
3. Install all frontend dependencies
4. Create initial `.env` configuration files from examples
5. Verify all installations

## Manual Setup (Step by Step)

If you prefer to set up manually or the script doesn't work for your system:

### Prerequisites
- Python 3.9+
- Node.js 18+
- Docker & Docker Compose (for running the full application)
- Git

### Step 1: Clone Repository

```bash
git clone https://github.com/palasangha/OCR_metadata_extraction.git
cd OCR_metadata_extraction
```

### Step 2: Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate

# On Windows:
# venv\Scripts\activate
```

### Step 3: Install Backend Dependencies

```bash
cd backend
pip install --upgrade pip
pip install -r requirements.txt
cd ..
```

### Step 4: Install Frontend Dependencies

```bash
cd frontend
npm ci
cd ..
```

### Step 5: Configure Environment Variables

```bash
# Copy example configurations
cp .env.example .env
cp .env.worker.example .env.worker

# Edit .env with your configuration
# Required values:
# - MONGO_ROOT_PASSWORD
# - SECRET_KEY
# - JWT_SECRET_KEY
# - GOOGLE_CLIENT_ID
# - GOOGLE_CLIENT_SECRET
# - etc.
```

### Step 6: Start the Application

**Option A: Using Docker Compose (Recommended)**
```bash
docker-compose up -d
```

**Option B: Manual Backend Start**
```bash
# Terminal 1: Start Backend
source venv/bin/activate
python backend/app.py
```

```bash
# Terminal 2: Start Frontend
cd frontend
npm run dev
```

## Troubleshooting

### Virtual Environment Issues
```bash
# If venv activation fails, try:
python3 -m venv --upgrade venv

# Verify activation (should show (venv) in prompt)
which python
```

### Frontend Build Errors
```bash
# If npm has issues:
rm -rf node_modules package-lock.json
npm ci
npm run build
```

### Port Already in Use
If ports 3000 (frontend), 5000 (backend), or 27017 (MongoDB) are in use:
```bash
# Find process using port 3000
lsof -i :3000

# Kill the process
kill -9 <PID>
```

### Docker Issues
```bash
# Rebuild images
docker-compose build --no-cache

# Restart services
docker-compose down
docker-compose up -d

# Check logs
docker-compose logs -f <service-name>
```

## Project Structure

```
OCR_metadata_extraction/
├── backend/                 # Python Flask API
│   ├── app/
│   │   ├── routes/         # API endpoints
│   │   ├── models/         # Database models
│   │   ├── services/       # Business logic
│   │   └── utils/          # Utilities
│   └── requirements.txt
├── frontend/               # React TypeScript UI
│   ├── src/
│   │   ├── components/
│   │   ├── services/
│   │   ├── types/
│   │   └── stores/
│   ├── package.json
│   └── package-lock.json
├── docker-compose.yml      # Service orchestration
├── setup.sh               # Automated setup script
├── .env.example           # Environment template
└── README.md              # Documentation
```

## Environment Variables Reference

### Backend (.env)
```
MONGO_ROOT_USERNAME=gvpocr_admin
MONGO_ROOT_PASSWORD=<your-password>
MONGO_URI=mongodb://mongodb:27017/gvpocr

SECRET_KEY=<your-secret-key>
JWT_SECRET_KEY=<your-jwt-secret>

GOOGLE_CLIENT_ID=<your-google-client-id>
GOOGLE_CLIENT_SECRET=<your-google-client-secret>
GOOGLE_REDIRECT_URI=http://localhost:3000/callback

DEFAULT_OCR_PROVIDER=google_vision
LMSTUDIO_HOST=http://lmstudio:1234

USE_NSQ=true
NSQD_ADDRESS=nsqd:4150
NSQLOOKUPD_ADDRESSES=nsqlookupd:4161
```

### Worker (.env.worker)
```
MONGO_URI=mongodb://mongodb:27017/gvpocr
NSQD_HOST=nsqd
NSQD_PORT=4150
```

## Common Commands

```bash
# Activate Python environment
source venv/bin/activate

# Deactivate Python environment
deactivate

# Start Docker containers
docker-compose up -d

# Stop Docker containers
docker-compose down

# View container logs
docker logs <container-name>
docker-compose logs -f

# Frontend development server
cd frontend && npm run dev

# Frontend production build
cd frontend && npm run build

# Backend development (if running outside Docker)
python backend/app.py

# Run tests
npm run test         # Frontend tests
pytest backend       # Backend tests
```

## Support

For issues or questions:
1. Check existing GitHub issues
2. Review the troubleshooting section above
3. Check container logs: `docker-compose logs`
4. Create a new issue with:
   - Error message
   - Steps to reproduce
   - System information (OS, Python version, Node version)
   - Docker version (if applicable)
