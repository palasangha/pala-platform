#!/bin/bash
# Script to create GitHub labels from labels.yml
# Requires: gh (GitHub CLI) to be installed and authenticated
# Usage: ./setup-labels.sh [owner/repo]

set -e

REPO=${1:-"palasangha/pala-platform"}

echo "🏷️  Setting up labels for $REPO"
echo ""

# Check if gh CLI is available
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed."
    echo "Please install it from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub CLI."
    echo "Please run: gh auth login"
    exit 1
fi

# Component Labels (blue)
echo "📦 Creating component labels..."
gh label create "component: processors" --repo "$REPO" --color "0075ca" --description "OCR, PalaScribe processors" --force 2>/dev/null || true
gh label create "component: mcp-server" --repo "$REPO" --color "0075ca" --description "MCP orchestrator" --force 2>/dev/null || true
gh label create "component: agents" --repo "$REPO" --color "0075ca" --description "All AI agents" --force 2>/dev/null || true
gh label create "component: storage" --repo "$REPO" --color "0075ca" --description "Storage layer" --force 2>/dev/null || true
gh label create "component: enrichment" --repo "$REPO" --color "0075ca" --description "Metadata, signing" --force 2>/dev/null || true
gh label create "component: web" --repo "$REPO" --color "0075ca" --description "Web portal" --force 2>/dev/null || true
gh label create "component: mobile" --repo "$REPO" --color "0075ca" --description "Mobile apps" --force 2>/dev/null || true
gh label create "component: infrastructure" --repo "$REPO" --color "0075ca" --description "DevOps, CI/CD" --force 2>/dev/null || true
gh label create "component: docs" --repo "$REPO" --color "0075ca" --description "Documentation" --force 2>/dev/null || true

# Type Labels (light blue for features/tasks, red for bugs)
echo "🏷️  Creating type labels..."
gh label create "type: feature" --repo "$REPO" --color "a2eeef" --description "New capability" --force 2>/dev/null || true
gh label create "type: task" --repo "$REPO" --color "a2eeef" --description "Work item (technical, non-user-facing)" --force 2>/dev/null || true
gh label create "type: bug" --repo "$REPO" --color "d73a4a" --description "Something broken" --force 2>/dev/null || true
gh label create "type: docs" --repo "$REPO" --color "a2eeef" --description "Documentation work" --force 2>/dev/null || true

# Size Labels (green to orange gradient)
echo "📏 Creating size labels..."
gh label create "size: small" --repo "$REPO" --color "c2e0c6" --description "Few hours" --force 2>/dev/null || true
gh label create "size: medium" --repo "$REPO" --color "fef2c0" --description "1-3 days" --force 2>/dev/null || true
gh label create "size: large" --repo "$REPO" --color "f9d0c4" --description "1+ week, needs breakdown" --force 2>/dev/null || true

# Priority Labels (red gradient)
echo "⚡ Creating priority labels..."
gh label create "priority: urgent" --repo "$REPO" --color "b60205" --description "Drop everything" --force 2>/dev/null || true
gh label create "priority: high" --repo "$REPO" --color "d93f0b" --description "This week" --force 2>/dev/null || true
gh label create "priority: medium" --repo "$REPO" --color "fbca04" --description "This month" --force 2>/dev/null || true
gh label create "priority: low" --repo "$REPO" --color "0e8a16" --description "Someday" --force 2>/dev/null || true

# Status Labels (optional)
echo "🚦 Creating status labels..."
gh label create "status: blocked" --repo "$REPO" --color "d4c5f9" --description "Blocked by external dependency" --force 2>/dev/null || true

echo ""
echo "✅ Labels created successfully!"
echo ""
echo "Next steps:"
echo "1. Create GitHub Project board: 'Pala Development'"
echo "2. Add columns: 📋 Backlog, 📝 To Do, 🚧 In Progress, ✅ Done"
echo "3. Enable automation (auto-add to Backlog, auto-move to Done)"
