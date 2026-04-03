#!/usr/bin/env bash
# Phase 2 Test & Deployment Guide
# =================================
# Quick reference for testing the Chat UI with RAG backend

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   PHASE 2: Chat UI Implementation - Testing Guide             ║"
echo "╚════════════════════════════════════════════════════════════════╝"

echo ""
echo "✅ PHASE 2 IMPLEMENTATION COMPLETE"
echo ""
echo "What's been added:"
echo "  • Chat tab in PalaWebDashboard"
echo "  • ChatPanel component with message history"
echo "  • Source documents display with relevance scores"
echo "  • Integration with chat-agent via WebSocket"
echo ""

echo "📋 DEPLOYMENT CHECKLIST"
echo "========================"
echo ""
echo "Step 1: Install dependencies"
echo "  └─ cd packages/PalaAgents/storage-agent && pip install -r requirements.txt"
echo "  └─ cd packages/PalaAgents/chat-agent && pip install -r requirements.txt"
echo ""

echo "Step 2: Start MCP server (if not already running)"
echo "  └─ npm run dev  # From workspace root"
echo ""

echo "Step 3: Start storage-agent"
echo "  └─ cd packages/PalaAgents/storage-agent"
echo "  └─ python main.py"
echo ""

echo "Step 4: Start chat-agent"
echo "  └─ cd packages/PalaAgents/chat-agent"
echo "  └─ export MCP_SERVER_URL='ws://localhost:3000'"
echo "  └─ export MCP_AGENT_ID='chat-agent'"
echo "  └─ python main.py"
echo ""

echo "Step 5: Start web dashboard"
echo "  └─ npm run dev  # From apps/web or workspace root"
echo ""

echo "Step 6: Open in browser and test"
echo "  └─ Navigate to: http://localhost:3000"
echo "  └─ Click 'Chat' tab"
echo "  └─ Ask a question about your documents"
echo ""

echo "📊 TESTING THE FLOW"
echo "==================="
echo ""
echo "1. Store test documents first (Developer tab)"
echo "   └─ Use storage-agent.store_document() to add documents"
echo "   └─ Embeddings will be generated automatically"
echo ""

echo "2. Search for documents (using semantic search)"
echo "   └─ In Chat tab: Ask about the documents you stored"
echo "   └─ e.g., 'Tell me about Buddhist meditation'"
echo ""

echo "3. View results"
echo "   └─ Message history shows Q&A"
echo "   └─ Source documents displayed with relevance scores"
echo "   └─ Responses include [doc-ID] citations"
echo ""

echo "🔧 MONITORING"
echo "=============="
echo ""
echo "Watch storage-agent logs:"
echo "  tail -f logs/storage-agent.log | grep '\\[CHAT-AGENT\\]\\|\\[SEMANTIC-SEARCH\\]'"
echo ""

echo "Watch chat-agent logs:"
echo "  tail -f logs/chat-agent.log | grep '\\[CHAT-AGENT\\]\\|\\[ORCHESTRATION\\]'"
echo ""

echo "🐛 TROUBLESHOOTING"
echo "=================="
echo ""
echo "❌ Chat not responding?"
echo "   ✓ Check if chat-agent is running and connected to MCP server"
echo "   ✓ Check logs: grep 'ERROR\\|❌' logs/chat-agent.log"
echo ""

echo "❌ No search results?"
echo "   ✓ Ensure documents are stored with embeddings"
echo "   ✓ Check logs: grep 'SEARCH-DOCUMENTS\\|embedding_generated' logs/storage-agent.log"
echo ""

echo "❌ WebSocket connection error?"
echo "   ✓ Verify MCP server is running on port 3000"
echo "   ✓ Check browser console for connection errors"
echo ""

echo "✅ STATUS: Phase 2 Ready for Testing"
echo "===================================="
echo ""
echo "The Chat interface is now integrated with the RAG backend."
echo "Follow the deployment checklist above to test end-to-end."
echo ""
