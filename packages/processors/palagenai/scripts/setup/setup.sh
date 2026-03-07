#!/bin/bash

# Setup script for GVPOCR project
# This script initializes a fresh clone with all dependencies

set -e  # Exit on error

echo "================================"
echo "GVPOCR Initial Setup Script"
echo "================================"

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if we're in a git repository
if [ ! -d "$SCRIPT_DIR/.git" ]; then
    echo "Error: Not in a git repository. Please clone the repository first."
    exit 1
fi

echo ""
echo "Step 1: Setting up Python Virtual Environment..."
echo "=================================================="

# Create Python virtual environment
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    python3 -m venv "$SCRIPT_DIR/venv"
    echo "✓ Python virtual environment created"
else
    echo "✓ Python virtual environment already exists"
fi

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"
echo "✓ Virtual environment activated"

echo ""
echo "Step 2: Installing Python Backend Dependencies..."
echo "==================================================="

cd "$SCRIPT_DIR/backend"

# Upgrade pip
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
echo "✓ pip upgraded"

# Install backend dependencies
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✓ Backend dependencies installed"
else
    echo "! requirements.txt not found in backend directory"
fi

cd "$SCRIPT_DIR"

echo ""
echo "Step 3: Installing Frontend Dependencies..."
echo "============================================"

cd "$SCRIPT_DIR/frontend"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "! Node.js is not installed. Please install Node.js v18+ first."
    echo "  Visit: https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "! Node.js v18+ is required. You have $(node --version)"
    exit 1
fi

echo "✓ Node.js version: $(node --version)"
echo "✓ npm version: $(npm --version)"

# Check for package.json
if [ ! -f "package.json" ]; then
    echo "! package.json not found in frontend directory"
    exit 1
fi

# Check for package-lock.json (required for npm ci)
if [ ! -f "package-lock.json" ]; then
    echo "! package-lock.json not found. Running npm install instead..."
    npm install
    echo "✓ Frontend dependencies installed (with package-lock.json generated)"
else
    echo "✓ package-lock.json found. Using npm ci for clean install..."
    npm ci
    echo "✓ Frontend dependencies installed"
fi

# Optional: Check for vulnerabilities
if command -v npm &> /dev/null; then
    VULN_COUNT=$(npm audit 2>/dev/null | grep -c "vulnerabilities" || echo "0")
    if [ "$VULN_COUNT" -gt 0 ]; then
        echo "⚠ Security vulnerabilities detected. Run: npm audit fix"
    fi
fi

cd "$SCRIPT_DIR"

echo ""
echo "Step 4: Environment Configuration..."
echo "====================================="

# Check for .env file
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    if [ -f "$SCRIPT_DIR/.env.example" ]; then
        cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
        echo "✓ Created .env from .env.example"
        echo "  IMPORTANT: Update .env with your configuration values"
    else
        echo "! .env.example not found. Cannot auto-create .env"
    fi
else
    echo "✓ .env file already exists"
fi

# Check for .env.worker file
if [ ! -f "$SCRIPT_DIR/.env.worker" ]; then
    if [ -f "$SCRIPT_DIR/.env.worker.example" ]; then
        cp "$SCRIPT_DIR/.env.worker.example" "$SCRIPT_DIR/.env.worker"
        echo "✓ Created .env.worker from .env.worker.example"
    else
        echo "! .env.worker.example not found. Cannot auto-create .env.worker"
    fi
else
    echo "✓ .env.worker file already exists"
fi

echo ""
echo "Step 5: Verification..."
echo "======================="

# Verify Python installation in venv
python --version
echo "✓ Python version verified"

# Verify Node.js
node --version
echo "✓ Node.js verified"

echo ""
echo "================================"
echo "Setup Complete!"
echo "================================"
echo ""
echo "Next Steps:"
echo "==========="
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Update .env with your configuration values"
echo ""
echo "3. Start the project:"
echo "   Backend:  python backend/app.py"
echo "   Frontend: cd frontend && npm run dev"
echo "   Docker:   docker-compose up -d"
echo ""
echo "4. View logs:"
echo "   docker logs <container-name>"
echo ""
echo "Virtual environment location: $SCRIPT_DIR/venv"
echo "To deactivate venv: deactivate"
echo ""
