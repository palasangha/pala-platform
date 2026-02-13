"""
Execution Monitor Service - Real-time task execution tracking.

Tracks task execution lifecycle, model usage, timing, errors, retries,
and queue status for the live execution dashboard.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid
import random


class ExecutionStatus:
    QUEUED = 'queued'
    RUNNING = 'running'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class ExecutionLog:
    """Represents one task execution record."""

    def __init__(self, task_name: str, agent_name: str, model_used: str,
                 status: str = ExecutionStatus.QUEUED, delegated_by: str = 'pala-jarvis'):
        self.id = str(uuid.uuid4())[:8]
        self.task_name = task_name
        self.agent_name = agent_name
        self.model_used = model_used
        self.status = status
        self.delegated_by = delegated_by
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        self.error: Optional[str] = None
        self.retry_count = 0
        self.log_lines: List[str] = []
        self.dependencies: List[str] = []

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.utcnow() - self.start_time).total_seconds()

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'task_name': self.task_name,
            'agent_name': self.agent_name,
            'model_used': self.model_used,
            'status': self.status,
            'delegated_by': self.delegated_by,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'error': self.error,
            'retry_count': self.retry_count,
            'log_lines': self.log_lines,
            'dependencies': self.dependencies,
        }


class ExecutionMonitorService:
    """Tracks and controls task execution lifecycle."""

    def __init__(self):
        self._logs: Dict[str, ExecutionLog] = {}
        self._seed_demo_logs()

    def get_logs(self, agent: Optional[str] = None, status: Optional[str] = None,
                 limit: int = 50) -> List[Dict]:
        logs = list(self._logs.values())
        if agent:
            logs = [l for l in logs if l.agent_name == agent]
        if status:
            logs = [l for l in logs if l.status == status]
        logs.sort(key=lambda l: l.start_time, reverse=True)
        return [l.to_dict() for l in logs[:limit]]

    def get_queue_status(self) -> Dict:
        all_logs = list(self._logs.values())
        return {
            'total': len(all_logs),
            'queued': sum(1 for l in all_logs if l.status == ExecutionStatus.QUEUED),
            'running': sum(1 for l in all_logs if l.status == ExecutionStatus.RUNNING),
            'paused': sum(1 for l in all_logs if l.status == ExecutionStatus.PAUSED),
            'completed': sum(1 for l in all_logs if l.status == ExecutionStatus.COMPLETED),
            'failed': sum(1 for l in all_logs if l.status == ExecutionStatus.FAILED),
            'cancelled': sum(1 for l in all_logs if l.status == ExecutionStatus.CANCELLED),
        }

    def create_log(self, task_name: str, agent_name: str, model_used: str,
                   delegated_by: str = 'pala-jarvis') -> Dict:
        log = ExecutionLog(task_name=task_name, agent_name=agent_name,
                           model_used=model_used, delegated_by=delegated_by)
        self._logs[log.id] = log
        return log.to_dict()

    def update_status(self, log_id: str, status: str, error: Optional[str] = None) -> Optional[Dict]:
        log = self._logs.get(log_id)
        if not log:
            return None
        log.status = status
        if status in (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED):
            log.end_time = datetime.utcnow()
        if error:
            log.error = error
            log.retry_count += 1
        log.log_lines.append(f'[{datetime.utcnow().strftime("%H:%M:%S")}] Status → {status}')
        return log.to_dict()

    def pause_task(self, log_id: str) -> Optional[Dict]:
        return self.update_status(log_id, ExecutionStatus.PAUSED)

    def cancel_task(self, log_id: str) -> Optional[Dict]:
        return self.update_status(log_id, ExecutionStatus.CANCELLED)

    def replay_task(self, log_id: str) -> Optional[Dict]:
        log = self._logs.get(log_id)
        if not log:
            return None
        # Create a new execution from the same task
        new_log = ExecutionLog(
            task_name=f'{log.task_name} (replay)',
            agent_name=log.agent_name,
            model_used=log.model_used,
            delegated_by=log.delegated_by,
        )
        new_log.status = ExecutionStatus.QUEUED
        new_log.dependencies = [log_id]
        self._logs[new_log.id] = new_log
        return new_log.to_dict()

    def _seed_demo_logs(self):
        """Pre-populate with demo execution data."""
        now = datetime.utcnow()
        demo_entries = [
            ('Build Tipitaka search index', 'database-architect', 'ollama:llama3.2-vision:latest',
             ExecutionStatus.COMPLETED, now - timedelta(hours=2), now - timedelta(hours=1, minutes=45)),
            ('Generate sutta embeddings', 'embeddings-trainer', 'claude-sonnet-4-20250514',
             ExecutionStatus.RUNNING, now - timedelta(minutes=30), None),
            ('Pali diacritics validation', 'pali-linguist', 'claude-sonnet-4-20250514',
             ExecutionStatus.COMPLETED, now - timedelta(hours=1), now - timedelta(minutes=50)),
            ('Dashboard responsive layout', 'flutter-web', 'gpt-4o',
             ExecutionStatus.RUNNING, now - timedelta(minutes=15), None),
            ('API rate limit middleware', 'flask-api', 'claude-sonnet-4-20250514',
             ExecutionStatus.QUEUED, now - timedelta(minutes=5), None),
            ('Docker compose optimization', 'docker-builder', 'ollama:llama3.2-vision:latest',
             ExecutionStatus.FAILED, now - timedelta(hours=3), now - timedelta(hours=2, minutes=50)),
            ('Unit test coverage report', 'test-runner', 'gpt-4o',
             ExecutionStatus.COMPLETED, now - timedelta(hours=4), now - timedelta(hours=3, minutes=30)),
            ('Token usage analysis', 'cost-tracker', 'claude-sonnet-4-20250514',
             ExecutionStatus.PAUSED, now - timedelta(minutes=45), None),
        ]

        for task_name, agent, model, status, start, end in demo_entries:
            log = ExecutionLog(task_name=task_name, agent_name=agent, model_used=model, status=status)
            log.start_time = start
            log.end_time = end
            log.log_lines = [
                f'[{start.strftime("%H:%M:%S")}] Task queued by pala-jarvis',
                f'[{(start + timedelta(seconds=5)).strftime("%H:%M:%S")}] Status → running',
            ]
            if status == ExecutionStatus.COMPLETED:
                log.log_lines.append(f'[{end.strftime("%H:%M:%S")}] Status → completed')
            elif status == ExecutionStatus.FAILED:
                log.error = 'Container build timeout after 600s'
                log.retry_count = 1
                log.log_lines.append(f'[{end.strftime("%H:%M:%S")}] ERROR: Container build timeout')
            self._logs[log.id] = log
