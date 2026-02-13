# Agent Communication Protocol

**Version:** 1.0
**Purpose:** Define how agents communicate with each other in Samma AI

---

## Overview

Claude Code doesn't have native peer-to-peer agent messaging. This protocol defines how to simulate agent communication using shared files and structured handoffs.

---

## Communication Patterns

### 1. Task Delegation Pattern

**Use Case:** Parent agent delegates work to sub-agent

```
Parent Agent
    |
    v
Create Task File (comms/tasks/{task_id}.json)
    |
    v
Sub-Agent reads task
    |
    v
Sub-Agent executes
    |
    v
Sub-Agent writes result (comms/results/{task_id}.json)
    |
    v
Parent Agent reads result
```

### 2. Broadcast Pattern

**Use Case:** Announce to all agents (e.g., system updates)

```
Any Agent
    |
    v
Write to comms/shared/announcements.json
    |
    v
All agents check announcements on startup
```

### 3. Direct Message Pattern

**Use Case:** One agent needs specific response from another

```
Agent A
    |
    v
Write to comms/inbox/{agent-b}.json
    |
    v
Agent B checks inbox
    |
    v
Agent B responds to comms/outbox/{agent-a}.json
```

---

## Message Formats

### Task Message

```json
{
  "id": "task-uuid",
  "type": "task",
  "from": "engineering-lead",
  "to": "flutter-web",
  "priority": "high|medium|low",
  "created_at": "2026-02-09T10:00:00Z",
  "deadline": null,
  "subject": "Create chat widget",
  "context": {
    "description": "Create a reusable chat widget for the dashboard",
    "requirements": ["responsive", "dark mode support"],
    "files": ["frontend/lib/widgets/"]
  },
  "status": "pending|in_progress|completed|failed"
}
```

### Result Message

```json
{
  "id": "task-uuid",
  "type": "result",
  "from": "flutter-web",
  "to": "engineering-lead",
  "completed_at": "2026-02-09T11:00:00Z",
  "status": "completed|failed",
  "result": {
    "files_created": ["frontend/lib/widgets/chat_widget.dart"],
    "files_modified": [],
    "summary": "Created responsive chat widget with dark mode support",
    "notes": "Used Provider for state management"
  },
  "errors": null
}
```

### Announcement Message

```json
{
  "id": "announcement-uuid",
  "type": "announcement",
  "from": "optimization-lead",
  "created_at": "2026-02-09T10:00:00Z",
  "expires_at": "2026-02-10T10:00:00Z",
  "priority": "high",
  "subject": "New model selection rules",
  "content": "Use Haiku for all simple lookups to reduce costs",
  "acknowledged_by": ["engineering-lead", "qa-lead"]
}
```

### Direct Message

```json
{
  "id": "msg-uuid",
  "type": "direct",
  "from": "tipitaka-lead",
  "to": "sutta-pitaka-expert",
  "created_at": "2026-02-09T10:00:00Z",
  "subject": "Need sutta reference",
  "content": "What is the reference for the Kalama Sutta?",
  "requires_response": true,
  "response_deadline": null
}
```

---

## Directory Structure

```
.claude/comms/
├── PROTOCOL.md          # This file
├── inbox/               # Incoming messages per agent
│   ├── engineering-lead.json
│   ├── tipitaka-lead.json
│   └── ...
├── outbox/              # Outgoing responses per agent
│   ├── engineering-lead.json
│   └── ...
├── tasks/               # Delegated tasks
│   └── {task-id}.json
├── results/             # Task results
│   └── {task-id}.json
└── shared/              # Broadcast messages
    ├── announcements.json
    └── status.json
```

---

## Agent Inbox Format

Each agent has an inbox file (`inbox/{agent-name}.json`):

```json
{
  "agent": "flutter-web",
  "last_checked": "2026-02-09T10:00:00Z",
  "messages": [
    {
      "id": "msg-1",
      "from": "engineering-lead",
      "subject": "...",
      "read": false,
      "...": "..."
    }
  ]
}
```

---

## Team Lead Communication

Team leads have additional responsibilities:

1. **Receive team-wide messages** - Messages to `/team engineering` go to `engineering-lead`
2. **Delegate to sub-agents** - Team lead decides which sub-agent handles the task
3. **Aggregate results** - Team lead consolidates results from sub-agents
4. **Report to user** - Team lead provides unified response

---

## Priority Levels

| Level | Meaning | Response Time |
|-------|---------|---------------|
| `critical` | Urgent, blocking issue | Immediate |
| `high` | Important, needed soon | Same session |
| `medium` | Standard priority | Within day |
| `low` | Nice to have | When available |

---

## Status Updates

Agents should update `shared/status.json` when:
- Starting a task
- Completing a task
- Encountering blockers
- Changing availability

```json
{
  "last_updated": "2026-02-09T10:00:00Z",
  "agents": {
    "flutter-web": {
      "status": "active|busy|idle|offline",
      "current_task": "task-uuid or null",
      "last_active": "2026-02-09T10:00:00Z"
    }
  }
}
```

---

## Best Practices

### For Sending Messages

1. Always include `id`, `from`, `to`, `created_at`
2. Be specific in `subject`
3. Provide full context - receiver may not have your context
4. Set appropriate priority
5. Specify if response is required

### For Receiving Messages

1. Check inbox at session start
2. Acknowledge high-priority messages first
3. Update status when starting task
4. Send result when complete
5. Clear processed messages

### For Team Leads

1. Monitor sub-agent inboxes
2. Redistribute work if agent is overloaded
3. Escalate blockers to user
4. Maintain team status

---

## Integration with Skills

| Skill | Purpose |
|-------|---------|
| `/team <name>` | Send message to team lead |
| `/agent <name>` | Send direct message to agent |
| `/status` | Check agent/team status |
| `/inbox` | Check your inbox |
| `/broadcast` | Send announcement to all |

---

## Example Workflow

**User:** "Add a new endpoint for bookmarks"

```
1. User sends to /team engineering
2. engineering-lead receives in inbox
3. engineering-lead creates task for flask-api
4. flask-api reads task from comms/tasks/
5. flask-api implements endpoint
6. flask-api writes result to comms/results/
7. engineering-lead reads result
8. engineering-lead reports to user
```

---

*This protocol enables structured agent communication in Samma AI*
