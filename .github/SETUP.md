# Project Management Setup Instructions

This document provides step-by-step instructions for setting up the complete project management system for Pala Platform.

## Quick Start

### 1. Create Labels (Automated)

Run the setup script to create all labels:

```bash
cd .github
./setup-labels.sh
```

This will create:
- 9 component labels (processors, mcp-server, agents, etc.)
- 4 type labels (feature, task, bug, docs)
- 3 size labels (small, medium, large)
- 4 priority labels (urgent, high, medium, low)
- 1 status label (blocked)

### 2. Create Project Board (Manual)

The GitHub Project board must be created through the UI:

1. **Navigate to Projects**
   - Go to: https://github.com/palasangha/pala-platform/projects
   - Click "New project"

2. **Create the Board**
   - Name: `Pala Development`
   - Template: Choose "Board"
   - Click "Create"

3. **Add Columns**
   
   Rename and configure the default columns:
   
   - **📋 Backlog**
     - Description: "Unsorted and unprioritized. Review weekly."
     - No limits
   
   - **📝 To Do**
     - Description: "Ready to work on. Limit: 5-10 items total"
     - Set WIP limit: 10
   
   - **🚧 In Progress**
     - Description: "Currently being worked on. Max 2 per person"
     - Set WIP limit: Based on team size
   
   - **✅ Done**
     - Description: "Closed issues from past 2 weeks"
     - No limits

4. **Enable Automation**
   
   Click on each column's "..." menu and configure:
   
   - **Backlog**: 
     - ✓ Auto-add items: "When issues are opened"
   
   - **Done**: 
     - ✓ Auto-add items: "When issues are closed"

5. **Configure Project Settings**
   - Go to project Settings (gear icon)
   - Enable: "Auto-archive items" after 14 days in Done
   - Visibility: Set to "Public" or "Private" as needed

### 3. Start Using the System

#### Creating Issues

1. Go to: https://github.com/palasangha/pala-platform/issues/new/choose
2. Select the appropriate template:
   - **Feature Request** - For new capabilities
   - **Task** - For technical work
   - **Bug Report** - For broken functionality
3. Fill in all required fields
4. Issue will automatically appear in 📋 Backlog

#### Weekly Workflow

**Monday Planning (15 minutes)**
1. Review Backlog - triage new issues
2. Move ready items to To Do
3. Each person assigns 2-3 issues to themselves
4. Quick sync on blockers and dependencies

**Daily Work (Async)**
- Move issue to In Progress when starting
- Comment with updates and blockers
- Link PRs to issues with "Fixes #123"
- Issue auto-moves to Done when PR merges

**Friday Review (15 minutes)**
- Review completed work in Done column
- Celebrate wins! 🎉
- Check for any blockers

#### Using Labels

Every issue should have:
- **1 Component label** - Which part of the system?
- **1 Type label** - What kind of work?
- **1 Size label** - How big is it?
- **1 Priority label** - When should it be done?

Example:
```
component: agents
type: feature
size: small
priority: high
```

#### Branch Naming

```bash
# For features
git checkout -b feature/issue-123-language-detection

# For bugs
git checkout -b fix/issue-456-ocr-rotation

# For tasks
git checkout -b task/issue-789-setup-turborepo
```

#### Linking PRs to Issues

In your PR description, use keywords to auto-close issues:

```markdown
Fixes #123
Closes #456
Resolves #789
```

When the PR merges, linked issues automatically move to Done.

## Troubleshooting

### Labels Not Created

If `setup-labels.sh` fails:

1. **Check GitHub CLI installation:**
   ```bash
   gh --version
   ```
   Install from: https://cli.github.com/

2. **Authenticate:**
   ```bash
   gh auth login
   ```

3. **Check permissions:**
   - You need write access to the repository
   - Personal access token needs `repo` scope

### Manual Label Creation

If the script doesn't work, create labels manually:

1. Go to: https://github.com/palasangha/pala-platform/labels
2. Click "New label"
3. Copy name, color, and description from `labels.yml`
4. Repeat for all labels

### Project Board Not Visible

- Check project visibility settings
- Ensure you have appropriate repository permissions
- Projects may not be enabled for the repository

## Reference

### Label Colors

- **Component labels**: Blue (`#0075ca`)
- **Type labels**: Light blue (`#a2eeef`) or Red for bugs (`#d73a4a`)
- **Size labels**: Green to Orange gradient (`#c2e0c6`, `#fef2c0`, `#f9d0c4`)
- **Priority labels**: Red gradient (`#b60205`, `#d93f0b`, `#fbca04`, `#0e8a16`)
- **Status labels**: Purple (`#d4c5f9`)

### Size Estimates

- **small**: 1-4 hours
- **medium**: 1-3 days
- **large**: 1+ week (break down into smaller issues)

### Priority Guidelines

- **urgent**: Security issues, production down, blocking launch
- **high**: Needed this week, important features
- **medium**: Needed this month, nice improvements
- **low**: Someday/maybe, technical debt

## Additional Resources

- See `Pala Platform - Project Management Guide.md` in repository root
- GitHub Projects documentation: https://docs.github.com/en/issues/planning-and-tracking-with-projects
- Issue templates documentation: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests

## Support

For questions or issues with the setup:
1. Check existing issues: https://github.com/palasangha/pala-platform/issues
2. Create a new issue using the Task template
3. Add label: `component: infrastructure`
