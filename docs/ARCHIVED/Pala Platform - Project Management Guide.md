# **Pala Platform \- Project Management Guide**

We use **GitHub Issues \+ One Project Board** for all project management. 

---

## **The System**

### **One Project Board: "Pala Development"**

**4 Columns:**

📋 Backlog  →  📝 To Do  →  🚧 In Progress  →  ✅ Done

#### **Column Rules**

**📋 Backlog**

* All new issues land here automatically  
* Unsorted and unprioritized  
* Review weekly to move items forward  
* Drag urgent items to top

**📝 To Do**

* Ready to work on   
* All details filled in  
* Assigned to someone  
* **Limit: 5-10 items total**

**🚧 In Progress**

* Currently being worked on  
* **Limit: Max 2 per person**  
* Must have assignee  
* Link PR when coding starts

**✅ Done**

* Closed issues from past 2 weeks  
* Auto-archived after 14 days  
* Celebrate wins\! 🎉

---

## **Labels**

### **Component Labels (Where)**

* `component: processors` \- OCR, PalaScribe  
* `component: mcp-server` \- MCP orchestrator  
* `component: agents` \- All AI agents  
* `component: storage` \- Storage layer  
* `component: enrichment` \- Metadata, signing  
* `component: web` \- Web portal  
* `component: mobile` \- Mobile apps  
* `component: infrastructure` \- DevOps, CI/CD  
* `component: docs` \- Documentation

### **Type Labels (What)**

* `type: feature` \- New capability  
* `type: task` \- Work item (technical, non-user-facing)  
* `type: bug` \- Something broken  
* `type: docs` \- Documentation work

### **Size Labels (How Big)**

* `size: small` \- Few hours  
* `size: medium` \- 1-3 days  
* `size: large` \- 1+ week, needs breakdown

### **Priority Labels (When)**

* `priority: urgent` \- Drop everything  
* `priority: high` \- This week  
* `priority: medium` \- This month  
* `priority: low` \- Someday

---

## **Issue Types**

### **Feature**

Use for new capabilities or enhancements.

**What to include:**

* **What & Why**: What is this and why do we need it?  
* **Scope**: What's in/out of scope  
* **Acceptance Criteria**: How do we know it's done? (checkboxes)  
* **Technical Notes**: Architecture decisions, dependencies  
* **Breakdown**: For large features, list sub-tasks

**Example:**

\#\# Feature: Metadata Agent \- Language Detection

\#\#\# What & Why  
\*\*What:\*\* Automatically detect the language of extracted text  
\*\*Why:\*\* Users need to filter content by language

\#\#\# Scope  
\*\*In Scope:\*\*  
\- Detect language using langdetect library  
\- Return ISO 639-1 language code  
\- Add to metadata schema

\*\*Out of Scope:\*\*  
\- Translation (future)  
\- Dialect detection (future)

\#\#\# Acceptance Criteria  
\- \[ \] Agent accepts text via MCP protocol  
\- \[ \] Returns language code (en, hi, pa, etc.)  
\- \[ \] Handles edge cases (short text, mixed languages)  
\- \[ \] Tests with 80%+ coverage  
\- \[ \] Documentation updated

\#\#\# Technical Notes  
\- Use langdetect npm package  
\- Fallback to "unknown" if confidence \< 50%  
\- Add to packages/agents/metadata-agent/src/extractors/

\#\#\# Breakdown (if size: large)  
\- \[ \] Install and configure langdetect  
\- \[ \] Implement detectLanguage() function  
\- \[ \] Add to metadata pipeline  
\- \[ \] Write tests  
\- \[ \] Update docs

\---  
Labels: type: feature, component: agents, size: small, priority: high  
Assignee: @username

---

### **Task**

Use for technical work that isn't user-facing.

**What to include:**

* **Description**: What needs to be done and why  
* **Details**: Specific steps  
* **Definition of Done**: Checkboxes for completion

**Example:**

\#\# Task: Setup Turborepo Configuration

\#\#\# Description  
Initialize monorepo with Turborepo for build optimization

\#\#\# Details  
\- Install Turborepo as dev dependency  
\- Create turbo.json with pipeline config  
\- Configure caching strategy  
\- Update root package.json scripts  
\- Document in README

\#\#\# Definition of Done  
\- \[ \] turbo.json exists with pipelines  
\- \[ \] pnpm dev runs all packages  
\- \[ \] pnpm build builds only changed packages  
\- \[ \] Cache working locally  
\- \[ \] Documentation updated

\---  
Labels: type: task, component: infrastructure, size: small, priority: high  
Assignee: @username

---

### **Bug**

Use when something is broken.

**What to include:**

* **What Happened**: Describe the bug  
* **Expected Behavior**: What should happen  
* **Steps to Reproduce**: How to recreate it  
* **Environment**: OS, browser, version (if relevant)

**Example:**

\#\# Bug: OCR Fails on Rotated Images

\#\#\# What Happened  
OCR engine returns empty string for rotated scanned documents

\#\#\# Expected Behavior  
Should detect rotation and auto-correct before processing

\#\#\# Steps to Reproduce  
1\. Upload rotated scan (attached: rotated-sample.jpg)  
2\. Run OCR processor  
3\. Get empty result

\#\#\# Root Cause (if known)  
Tesseract doesn't auto-rotate by default

\#\#\# Fix  
\- Add orientation detection  
\- Rotate image before OCR  
\- Add tests with rotated samples

\---  
Labels: type: bug, component: processors, priority: high  
Estimate: 4 hours  
Assignee: @username

---

## **Handling Large Features**

When a feature has `size: large`, break it down using one of these patterns:

### **Pattern 1: Checklist in Issue (Preferred)**

\#\# Feature: Web Portal Authentication

\#\#\# Breakdown  
\- \[ \] \#123 Setup Auth0 integration  
\- \[ \] \#124 Create login page  
\- \[ \] \#125 Create signup page  
\- \[ \] \#126 Protected routes middleware  
\- \[ \] \#127 User session management  
\- \[ \] \#128 Logout functionality  
\- \[ \] \#129 Tests for auth flows

\*\*Progress:\*\* 2/7 complete

---

## **Weekly Workflow**

### **Monday Planning (15 minutes)**

**Step 1: Review Backlog (5 min)**

* Any urgent bugs? → Add `priority: urgent` → Move to To Do  
* What aligns with the current milestone? → Move to To Do  
* Large features broken down? → Add breakdown or create sub-issues  
* Any blocked issues unblocked? → Move to To Do

**Step 2: Plan the Week (5 min)**

* Each person picks 2-3 issues from To Do  
* Assign yourself  
* Verify details are clear  
* Check capacity (don't overcommit\!)

**Step 3: Quick Sync (5 min)**

* Anyone blocked?  
* Architectural questions?  
* Dependencies between tasks?  
* Good to go\!

---

### **Daily Work (Async)**

**When starting:**

1. Move issue from To Do → In Progress  
2. Comment: "Starting work on this"  
3. Create branch: `git checkout -b feature/issue-123-name`

**While working:**

* Update issue with progress  
* Ask questions in comments (tag teammates)  
* Link PR when you open it

**When blocked:**

* Comment explaining blocker  
* Add `status: blocked` label (create if needed)  
* Tag person who can unblock  
* Pick up another task

**When done:**

* Create PR linking issue: "Fixes \#123"  
* Request review  
* Issue auto-moves to Done when PR merges

---

## **Quick Reference**

COLUMNS:  
📋 Backlog        → Unsorted, review weekly  
📝 To Do          → Ready this week, assigned (5-10 items)  
🚧 In Progress    → Working now (max 2 per person)  
✅ Done           → Closed, auto-archives after 14 days

SIZE ESTIMATES:  
small     → Few hours  
medium    → 1-3 days  
large     → 1+ week (needs breakdown)

PRIORITIES:  
urgent    → Drop everything  
high      → This week  
medium    → This month  
low       → Someday

LINKING:  
Fixes \#123        → Auto-closes issue on PR merge  
Depends on \#123   → Blocked until done  
Related \#123      → Reference only

WEEKLY RHYTHM:  
Monday    → Plan week (15 min)  
Daily     → Update issues, move cards (async)  
Friday    → Review and celebrate (15 min)

---

## **Next Steps**

1. Create project board: "Pala Development"  
2. Add 4 columns: Backlog, To Do, In Progress, Done  
3. Enable automation (auto-add to Backlog, auto-move to Done)  
4. Create labels (component, type, size, priority)  
5. Create issue templates (feature, task, bug)  
6. Create issues for current work  
7. Add labels and move to appropriate columns  
8. Start using in daily work  
9. Adjust as needed

