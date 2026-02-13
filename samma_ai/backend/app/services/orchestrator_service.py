"""
Orchestrator Service - Pala-Jarvis project manager agent.

Implements the orchestration layer where Pala-Jarvis coordinates work
across team leaders and sub-agents.
"""

from datetime import datetime
from typing import Dict, List, Optional
import uuid


class EscalationLevel:
    AGENT = 'agent'
    TEAM_LEADER = 'team_leader'
    ORCHESTRATOR = 'orchestrator'
    USER = 'user'


class TaskDelegation:
    """Represents a delegated task flowing through the hierarchy."""

    def __init__(self, task_id: str, description: str, delegated_to: str,
                 delegated_by: str = 'pala-jarvis', priority: str = 'medium'):
        self.task_id = task_id
        self.description = description
        self.delegated_to = delegated_to
        self.delegated_by = delegated_by
        self.priority = priority
        self.status = 'pending'
        self.created_at = datetime.utcnow()
        self.result = None
        self.retry_count = 0
        self.escalation_level = EscalationLevel.ORCHESTRATOR
        self.notifications: List[Dict] = []

    def to_dict(self) -> Dict:
        return {
            'task_id': self.task_id,
            'description': self.description,
            'delegated_to': self.delegated_to,
            'delegated_by': self.delegated_by,
            'priority': self.priority,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'result': self.result,
            'retry_count': self.retry_count,
            'escalation_level': self.escalation_level,
            'notifications': self.notifications,
        }


class PalaJarvisOrchestrator:
    """
    Pala-Jarvis: the project manager agent.

    Escalation flow:  Agent → Team Leader → Pala-Jarvis → User
    User is notified only for: permission issues, human decisions,
    critical conflicts, unresolved execution failures.
    """

    # Agent → Team mapping
    TEAM_LEADERS = {
        'engineering': 'engineering-lead',
        'tipitaka-mastery': 'tipitaka-lead',
        'quality-assurance': 'qa-lead',
        'ai-ml': 'ai-lead',
        'devops': 'devops-lead',
        'optimization': 'optimization-lead',
    }

    AGENT_TO_TEAM = {
        'flutter-web': 'engineering', 'flask-api': 'engineering', 'database-architect': 'engineering',
        'sutta-pitaka-expert': 'tipitaka-mastery', 'vinaya-pitaka-expert': 'tipitaka-mastery',
        'abhidhamma-expert': 'tipitaka-mastery', 'pali-linguist': 'tipitaka-mastery',
        'code-reviewer': 'quality-assurance', 'test-runner': 'quality-assurance',
        'claude-integrator': 'ai-ml', 'embeddings-trainer': 'ai-ml',
        'docker-builder': 'devops', 'ci-cd': 'devops',
        'token-optimizer': 'optimization', 'model-selector': 'optimization',
        'context-manager': 'optimization', 'cost-tracker': 'optimization',
    }
    # Include leads themselves
    for _team, _lead in TEAM_LEADERS.items():
        AGENT_TO_TEAM[_lead] = _team

    def __init__(self):
        self._delegations: Dict[str, TaskDelegation] = {}
        self._user_notifications: List[Dict] = []

    def delegate_task(self, description: str, target_team: Optional[str] = None,
                      priority: str = 'medium') -> Dict:
        """Delegate a task. Routes to the appropriate team leader."""
        task_id = str(uuid.uuid4())[:8]

        # Auto-route by keyword matching if no target specified
        if not target_team:
            target_team = self._auto_route(description)

        team_leader = self.TEAM_LEADERS.get(target_team, 'engineering-lead')

        delegation = TaskDelegation(
            task_id=task_id,
            description=description,
            delegated_to=team_leader,
            priority=priority,
        )
        self._delegations[task_id] = delegation

        return delegation.to_dict()

    def get_delegations(self) -> List[Dict]:
        return [d.to_dict() for d in self._delegations.values()]

    def update_delegation_status(self, task_id: str, status: str, result: Optional[str] = None) -> Optional[Dict]:
        delegation = self._delegations.get(task_id)
        if not delegation:
            return None

        delegation.status = status
        if result:
            delegation.result = result

        # Check if escalation to user is needed
        if status == 'failed':
            delegation.retry_count += 1
            if delegation.retry_count >= 3:
                self._escalate_to_user(delegation, 'Execution failure unresolved after 3 retries')

        if status == 'conflict':
            self._escalate_to_user(delegation, 'Critical conflict requires human decision')

        if status == 'permission_required':
            self._escalate_to_user(delegation, 'Permission issue — human authorization needed')

        return delegation.to_dict()

    def get_user_notifications(self) -> List[Dict]:
        return list(self._user_notifications)

    def clear_notification(self, notification_id: str):
        self._user_notifications = [n for n in self._user_notifications if n['id'] != notification_id]

    # ── Private ───────────────────────────────────────────────────────

    def _auto_route(self, description: str) -> str:
        desc_lower = description.lower()
        routing_keywords = {
            'engineering': ['build', 'flutter', 'api', 'database', 'schema', 'frontend', 'backend', 'code'],
            'tipitaka-mastery': ['sutta', 'vinaya', 'abhidhamma', 'pali', 'tipitaka', 'dhamma', 'teaching'],
            'quality-assurance': ['test', 'review', 'quality', 'bug', 'fix', 'security', 'audit'],
            'ai-ml': ['ai', 'model', 'claude', 'embedding', 'prompt', 'rag', 'llm'],
            'devops': ['deploy', 'docker', 'ci/cd', 'pipeline', 'infrastructure', 'container'],
            'optimization': ['optimize', 'token', 'cost', 'performance', 'cache', 'compress'],
        }
        best_team = 'engineering'
        best_score = 0
        for team, keywords in routing_keywords.items():
            score = sum(1 for kw in keywords if kw in desc_lower)
            if score > best_score:
                best_score = score
                best_team = team
        return best_team

    def _escalate_to_user(self, delegation: TaskDelegation, reason: str):
        delegation.escalation_level = EscalationLevel.USER
        notification = {
            'id': str(uuid.uuid4())[:8],
            'task_id': delegation.task_id,
            'reason': reason,
            'description': delegation.description,
            'delegated_to': delegation.delegated_to,
            'timestamp': datetime.utcnow().isoformat(),
        }
        delegation.notifications.append(notification)
        self._user_notifications.append(notification)
