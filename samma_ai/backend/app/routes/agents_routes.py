"""
Agents Routes - API endpoints for agent management, orchestration,
collaboration, and execution monitoring.
"""

from flask import Blueprint, request, jsonify
from app.services.orchestrator_service import PalaJarvisOrchestrator
from app.services.collaboration_service import CollaborationService
from app.services.execution_monitor_service import ExecutionMonitorService

agents_bp = Blueprint('agents', __name__)

# Service singletons
orchestrator = PalaJarvisOrchestrator()
collaboration = CollaborationService()
execution_monitor = ExecutionMonitorService()


# ── Agent Hierarchy ───────────────────────────────────────────────────

@agents_bp.route('/agents', methods=['GET'])
def list_agents():
    """List all agents with hierarchy, status, and model info."""
    hierarchy = {
        'orchestrator': {
            'name': 'pala-jarvis',
            'displayName': 'Pala-Jarvis',
            'role': 'orchestrator',
            'description': 'Project Manager — coordinates all teams',
            'status': 'active',
            'defaultModel': 'claude-sonnet-4-20250514',
        },
        'teams': {
            team: {
                'lead': lead,
                'agents': [a for a, t in orchestrator.AGENT_TO_TEAM.items() if t == team and a != lead],
            }
            for team, lead in orchestrator.TEAM_LEADERS.items()
        },
    }
    return jsonify(hierarchy)


# ── Pala-Jarvis Delegation ────────────────────────────────────────────

@agents_bp.route('/agents/delegate', methods=['POST'])
def delegate_task():
    """Delegate a task through Pala-Jarvis."""
    data = request.get_json()
    if not data or 'description' not in data:
        return jsonify({'error': 'description is required'}), 400

    result = orchestrator.delegate_task(
        description=data['description'],
        target_team=data.get('target_team'),
        priority=data.get('priority', 'medium'),
    )
    return jsonify(result)


@agents_bp.route('/agents/delegations', methods=['GET'])
def get_delegations():
    """Get all task delegations."""
    return jsonify({'delegations': orchestrator.get_delegations()})


@agents_bp.route('/agents/notifications', methods=['GET'])
def get_notifications():
    """Get user-facing notifications from Pala-Jarvis."""
    return jsonify({'notifications': orchestrator.get_user_notifications()})


# ── Execution Monitor ─────────────────────────────────────────────────

@agents_bp.route('/agents/execution-logs', methods=['GET'])
def get_execution_logs():
    """Get execution logs with optional filters."""
    agent = request.args.get('agent')
    status = request.args.get('status')
    limit = int(request.args.get('limit', 50))
    logs = execution_monitor.get_logs(agent=agent, status=status, limit=limit)
    queue = execution_monitor.get_queue_status()
    return jsonify({'logs': logs, 'queue_status': queue})


@agents_bp.route('/agents/execution/<log_id>/pause', methods=['POST'])
def pause_execution(log_id):
    result = execution_monitor.pause_task(log_id)
    if not result:
        return jsonify({'error': 'Log not found'}), 404
    return jsonify(result)


@agents_bp.route('/agents/execution/<log_id>/cancel', methods=['POST'])
def cancel_execution(log_id):
    result = execution_monitor.cancel_task(log_id)
    if not result:
        return jsonify({'error': 'Log not found'}), 404
    return jsonify(result)


@agents_bp.route('/agents/execution/<log_id>/replay', methods=['POST'])
def replay_execution(log_id):
    result = execution_monitor.replay_task(log_id)
    if not result:
        return jsonify({'error': 'Log not found'}), 404
    return jsonify(result)


# ── Collaboration Space ───────────────────────────────────────────────

@agents_bp.route('/agents/collaboration/threads', methods=['GET'])
def get_threads():
    """List collaboration threads with optional tag/search filter."""
    tag = request.args.get('tag')
    search = request.args.get('search')
    threads = collaboration.get_threads(tag=tag, search=search)
    return jsonify({'threads': threads})


@agents_bp.route('/agents/collaboration/threads/<thread_id>', methods=['GET'])
def get_thread(thread_id):
    """Get a single thread with messages."""
    thread = collaboration.get_thread(thread_id)
    if not thread:
        return jsonify({'error': 'Thread not found'}), 404
    return jsonify(thread)


@agents_bp.route('/agents/collaboration/threads', methods=['POST'])
def create_thread():
    """Create a new collaboration thread."""
    data = request.get_json()
    if not data or 'title' not in data:
        return jsonify({'error': 'title is required'}), 400

    thread = collaboration.create_thread(
        title=data['title'],
        created_by=data.get('created_by', 'user'),
        tags=data.get('tags', []),
    )
    return jsonify(thread), 201


@agents_bp.route('/agents/collaboration/threads/<thread_id>/messages', methods=['POST'])
def add_thread_message(thread_id):
    """Add a message to a collaboration thread."""
    data = request.get_json()
    if not data or 'content' not in data:
        return jsonify({'error': 'content is required'}), 400

    msg = collaboration.add_message(
        thread_id=thread_id,
        from_agent=data.get('from_agent', 'user'),
        content=data['content'],
        tags=data.get('tags', []),
    )
    if not msg:
        return jsonify({'error': 'Thread not found'}), 404
    return jsonify(msg), 201
