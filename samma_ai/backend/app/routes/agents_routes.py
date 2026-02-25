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


# ── Agent Direct Messaging ────────────────────────────────────────────

@agents_bp.route('/agents/chat', methods=['POST'])
def agent_chat():
    """
    Send a message to an agent and get AI-powered response.
    Uses same model routing as Samma AI chatbot (Copilot -> Claude -> OpenAI).

    Request:
        {
            "agent_name": "pala-jarvis",
            "message": "Can you help me with...",
            "conversation_id": "optional-uuid"
        }

    Response:
        {
            "id": "message-uuid",
            "conversation_id": "conversation-uuid",
            "agent_name": "pala-jarvis",
            "user_message": "...",
            "agent_response": "...",
            "timestamp": "2026-02-16T10:00:00Z"
        }
    """
    from app.services.model_router_service import ModelRouterService
    from app import mongo
    import uuid
    from datetime import datetime

    data = request.get_json()

    if not data or 'message' not in data or 'agent_name' not in data:
        return jsonify({'error': 'message and agent_name are required'}), 400

    agent_name = data['agent_name']
    message = data['message']
    conversation_id = data.get('conversation_id', str(uuid.uuid4()))

    try:
        # Initialize model router
        model_router = ModelRouterService()

        # Build agent-specific system prompt
        agent_prompts = {
            'pala-jarvis': """You are Pala-Jarvis, the project manager and orchestrator for the Samma AI project.
Your role is to coordinate teams, delegate tasks, and help users with project management decisions.
Be professional, helpful, and concise. You can delegate tasks to specialized team leaders when needed.""",

            'engineering-lead': """You are the Engineering Lead for Samma AI.
You handle architecture decisions, design documentation, and coordinate Flutter/Flask development.
Be technical and detailed in your responses.""",

            'tipitaka-lead': """You are the Tipitaka Mastery Team Lead.
You navigate the Tipitaka structure and coordinate domain experts for Buddhist canonical texts.
Be scholarly and precise, always grounding responses in canonical evidence.""",

            'qa-lead': """You are the QA Lead for Samma AI.
You plan testing strategies, review code quality, and ensure release readiness.
Be thorough and detail-oriented.""",

            'ai-lead': """You are the AI/ML Team Lead.
You handle AI strategy, prompt engineering, and Claude API integration.
Be knowledgeable about LLMs and machine learning best practices.""",

            'devops-lead': """You are the DevOps Lead.
You handle infrastructure planning, Docker containerization, and CI/CD pipelines.
Be practical and focused on deployment and operations.""",

            'optimization-lead': """You are the Optimization Team Lead.
You focus on token efficiency, model selection, cost management, and performance optimization.
Be analytical and cost-conscious.""",
        }

        system_prompt = agent_prompts.get(agent_name, f"""You are {agent_name}, an AI agent in the Samma AI project.
Be helpful, professional, and respond according to your role.""")

        # Use same model as Samma AI chatbot (defaults to 'copilot')
        # This uses the model router's fallback chain: copilot -> claude -> openai (-> ollama if enabled)
        agent_response = model_router.route_request(
            prompt=message,
            model_id='copilot',  # Same default as Samma AI chatbot
            system_prompt=system_prompt
        )

        # Save conversation to MongoDB
        message_id = str(uuid.uuid4())
        try:
            mongo.db.agent_conversations.insert_one({
                'id': message_id,
                'conversation_id': conversation_id,
                'agent_name': agent_name,
                'user_message': message,
                'agent_response': agent_response,
                'timestamp': datetime.utcnow()
            })
        except Exception as mongo_error:
            # Log but don't fail if MongoDB is unavailable
            from flask import current_app
            current_app.logger.warning(f"Failed to save agent conversation: {mongo_error}")

        return jsonify({
            'id': message_id,
            'conversation_id': conversation_id,
            'agent_name': agent_name,
            'user_message': message,
            'agent_response': agent_response,
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/agents/chat/history/<conversation_id>', methods=['GET'])
def get_agent_chat_history(conversation_id):
    """Get chat history for an agent conversation."""
    from app import mongo

    try:
        history = list(mongo.db.agent_conversations.find(
            {'conversation_id': conversation_id},
            {'_id': 0}
        ).sort('timestamp', 1))

        return jsonify({
            'conversation_id': conversation_id,
            'messages': history
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/agents/<agent_name>/conversations', methods=['GET'])
def get_agent_conversations(agent_name):
    """Get all conversations for a specific agent."""
    from app import mongo

    try:
        # Get unique conversation IDs for this agent
        conversations = mongo.db.agent_conversations.aggregate([
            {'$match': {'agent_name': agent_name}},
            {'$sort': {'timestamp': -1}},
            {'$group': {
                '_id': '$conversation_id',
                'last_message': {'$first': '$user_message'},
                'last_timestamp': {'$first': '$timestamp'},
                'message_count': {'$sum': 1}
            }},
            {'$sort': {'last_timestamp': -1}},
            {'$limit': 50}
        ])

        result = []
        for conv in conversations:
            result.append({
                'conversation_id': conv['_id'],
                'last_message': conv['last_message'],
                'last_timestamp': conv['last_timestamp'].isoformat() if conv.get('last_timestamp') else None,
                'message_count': conv['message_count']
            })

        return jsonify({
            'agent_name': agent_name,
            'conversations': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Pala Jarvis with Full Codebase Access ────────────────────────────

@agents_bp.route('/agents/pala-jarvis/chat', methods=['POST'])
def pala_jarvis_chat():
    """
    Chat with Pala Jarvis with FULL codebase access.

    This endpoint gives Pala Jarvis Claude Code-like capabilities:
    - Read/write files
    - Execute bash commands
    - Search code
    - Full project context

    Uses Claude Sonnet 4.5 with tool use.

    Request:
        {
            "message": "Help me implement feature X",
            "conversation_id": "optional-uuid"
        }

    Response:
        {
            "response": "AI response text",
            "tool_calls": [{tool, input, result}, ...],
            "conversation_id": "uuid",
            "timestamp": "ISO-8601"
        }
    """
    from app.services.pala_jarvis_service import PalaJarvisService
    from app import mongo
    import uuid
    from datetime import datetime

    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({'error': 'message is required'}), 400

    message = data['message']
    conversation_id = data.get('conversation_id', str(uuid.uuid4()))
    session_id = request.headers.get('X-Session-ID')  # Get OAuth session ID from header

    try:
        # Load conversation history from MongoDB
        conversation_history = []
        try:
            history_docs = mongo.db.pala_jarvis_conversations.find(
                {'conversation_id': conversation_id}
            ).sort('timestamp', 1)

            for doc in history_docs:
                # Reconstruct message format
                if 'messages' in doc:
                    conversation_history.extend(doc['messages'])
        except Exception as mongo_error:
            from flask import current_app
            current_app.logger.warning(f"Failed to load conversation history: {mongo_error}")

        # Get OAuth token if available
        session_token = None
        if session_id:
            from app.routes.auth_routes import get_user_token
            session_token = get_user_token(session_id)

        # Initialize Pala Jarvis service
        jarvis = PalaJarvisService()

        # Chat with full codebase access (with OAuth token if available)
        result = jarvis.chat(message, conversation_history, session_token=session_token)

        # Save conversation to MongoDB
        try:
            mongo.db.pala_jarvis_conversations.insert_one({
                'conversation_id': conversation_id,
                'timestamp': datetime.utcnow(),
                'user_message': message,
                'agent_response': result['response'],
                'tool_calls': result['tool_calls'],
                'messages': result['conversation']
            })
        except Exception as mongo_error:
            from flask import current_app
            current_app.logger.warning(f"Failed to save Pala Jarvis conversation: {mongo_error}")

        return jsonify({
            'response': result['response'],
            'tool_calls': result['tool_calls'],
            'conversation_id': conversation_id,
            'timestamp': datetime.utcnow().isoformat(),
            'stop_reason': result.get('stop_reason', 'complete')
        })

    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Pala Jarvis chat error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/agents/pala-jarvis/conversations', methods=['GET'])
def get_pala_jarvis_conversations():
    """Get all Pala Jarvis conversations."""
    from app import mongo

    try:
        conversations = mongo.db.pala_jarvis_conversations.aggregate([
            {'$sort': {'timestamp': -1}},
            {'$group': {
                '_id': '$conversation_id',
                'last_message': {'$first': '$user_message'},
                'last_timestamp': {'$first': '$timestamp'},
                'message_count': {'$sum': 1}
            }},
            {'$sort': {'last_timestamp': -1}},
            {'$limit': 50}
        ])

        result = []
        for conv in conversations:
            result.append({
                'conversation_id': conv['_id'],
                'last_message': conv['last_message'],
                'last_timestamp': conv['last_timestamp'].isoformat() if conv.get('last_timestamp') else None,
                'message_count': conv['message_count']
            })

        return jsonify({
            'conversations': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
