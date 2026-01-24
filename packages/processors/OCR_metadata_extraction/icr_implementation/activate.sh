#!/bin/bash
# ICR Quick Start Script
# Activates venv and provides helpful commands

echo "=================================="
echo "🚀 ICR Implementation Environment"
echo "=================================="
echo ""

# Activate virtual environment
source venv/bin/activate

echo "✅ Virtual environment activated"
echo ""
echo "📦 Installed packages:"
pip list | grep -E "(numpy|opencv|fastapi|pydantic|pillow|pytest)" | column -t
echo ""
echo "⏳ Pending installations:"
echo "  - paddleocr, paddlepaddle (Phase 1)"
echo "  - transformers, torch (Phase 2)"
echo "  - langchain, chromadb (Phase 4)"
echo ""
echo "💡 Quick Commands:"
echo "  Run all tests:     python run_icr_project.py"
echo "  Install Phase 1:   pip install paddleocr paddlepaddle"
echo "  Install all deps:  pip install -r requirements.txt"
echo "  View status:       cat DEPLOYMENT_STATUS.md"
echo ""
echo "📁 Current directory: $(pwd)"
echo ""

# Keep shell open
exec $SHELL
