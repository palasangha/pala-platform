# GitHub Configuration

GitHub Actions workflows, issue templates, and project management setup.

## Contents

### Issue Templates

Three issue templates are available when creating new issues:

- **Feature Request** (`ISSUE_TEMPLATE/feature.yml`) - For new capabilities or enhancements
- **Task** (`ISSUE_TEMPLATE/task.yml`) - For technical work that isn't user-facing
- **Bug Report** (`ISSUE_TEMPLATE/bug.yml`) - When something is broken

Each template includes structured fields based on our project management guide.

### Labels

Labels are defined in `labels.yml` and organized into four categories:

**Component Labels** (Where):
- `component: processors` - OCR, PalaScribe
- `component: mcp-server` - MCP orchestrator
- `component: agents` - All AI agents
- `component: storage` - Storage layer
- `component: enrichment` - Metadata, signing
- `component: web` - Web portal
- `component: mobile` - Mobile apps
- `component: infrastructure` - DevOps, CI/CD
- `component: docs` - Documentation

**Type Labels** (What):
- `type: feature` - New capability
- `type: task` - Work item (technical, non-user-facing)
- `type: bug` - Something broken
- `type: docs` - Documentation work

**Size Labels** (How Big):
- `size: small` - Few hours
- `size: medium` - 1-3 days
- `size: large` - 1+ week, needs breakdown

**Priority Labels** (When):
- `priority: urgent` - Drop everything
- `priority: high` - This week
- `priority: medium` - This month
- `priority: low` - Someday

### Setup Script

Run `./setup-labels.sh` to create all labels in the repository. Requires GitHub CLI (`gh`) to be installed and authenticated.

```bash
# Install labels for this repo
./setup-labels.sh

# Or for a different repo
./setup-labels.sh owner/repo
```

## Project Board Setup

The GitHub Project board must be created manually through the GitHub UI:

1. Go to repository Projects tab
2. Create new Project: "Pala Development"
3. Choose "Board" view
4. Add 4 columns:
   - 📋 **Backlog** - Unsorted, review weekly
   - 📝 **To Do** - Ready this week, assigned (5-10 items)
   - 🚧 **In Progress** - Working now (max 2 per person)
   - ✅ **Done** - Closed, auto-archives after 14 days
5. Enable automation:
   - Auto-add new issues to Backlog
   - Auto-move closed issues to Done

## Workflows

- `workflows/` - CI/CD workflows (coming soon)

## Documentation

See the root-level "Pala Platform - Project Management Guide.md" for complete workflow documentation.
