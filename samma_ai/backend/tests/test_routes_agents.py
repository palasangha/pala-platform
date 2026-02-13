import json
import pytest


class TestAgentHierarchy:
    """Tests for agent hierarchy endpoint."""

    def test_get_agents(self, client):
        """Test listing agent hierarchy."""
        response = client.get('/api/agents')
        assert response.status_code == 200
        data = json.loads(response.data)
        # Response has 'orchestrator' and 'teams' keys
        assert 'orchestrator' in data
        assert 'teams' in data
        # Orchestrator should be Pala-Jarvis
        assert 'jarvis' in data['orchestrator'].get('name', '').lower() or \
               'pala' in data['orchestrator'].get('name', '').lower()


class TestDelegation:
    """Tests for Pala-Jarvis task delegation."""

    def test_delegate_task(self, client):
        """Test delegating a task through Pala-Jarvis."""
        response = client.post(
            '/api/agents/delegate',
            data=json.dumps({
                'description': 'Test task for unit testing',
                'priority': 'medium'
            }),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        # Response should contain delegation info
        assert 'description' in data
        assert 'delegated_by' in data

    def test_delegate_task_missing_description(self, client):
        """Test delegation with missing description."""
        response = client.post(
            '/api/agents/delegate',
            data=json.dumps({'priority': 'high'}),
            content_type='application/json'
        )
        assert response.status_code in [200, 400]

    def test_get_delegations(self, client):
        """Test retrieving delegations."""
        response = client.get('/api/agents/delegations')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'delegations' in data
        assert isinstance(data['delegations'], list)


class TestExecutionMonitor:
    """Tests for execution monitoring endpoints."""

    def test_get_execution_logs(self, client):
        """Test fetching execution logs."""
        response = client.get('/api/agents/execution-logs')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'logs' in data
        assert isinstance(data['logs'], list)

    def test_get_execution_logs_filter_status(self, client):
        """Test filtering execution logs by status."""
        response = client.get('/api/agents/execution-logs?status=running')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'logs' in data

    def test_get_execution_logs_filter_agent(self, client):
        """Test filtering execution logs by agent."""
        response = client.get('/api/agents/execution-logs?agent=vinaya-lead')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'logs' in data

    def test_pause_execution(self, client):
        """Test pausing an execution."""
        # First get logs to find a valid ID
        logs_response = client.get('/api/agents/execution-logs')
        logs_data = json.loads(logs_response.data)
        if logs_data.get('logs'):
            log_id = logs_data['logs'][0].get('id', 'test-id')
            response = client.post(f'/api/agents/execution/{log_id}/pause')
            assert response.status_code in [200, 400, 404]

    def test_cancel_execution(self, client):
        """Test cancelling an execution."""
        logs_response = client.get('/api/agents/execution-logs')
        logs_data = json.loads(logs_response.data)
        if logs_data.get('logs'):
            log_id = logs_data['logs'][0].get('id', 'test-id')
            response = client.post(f'/api/agents/execution/{log_id}/cancel')
            assert response.status_code in [200, 400, 404]

    def test_replay_execution(self, client):
        """Test replaying an execution."""
        logs_response = client.get('/api/agents/execution-logs')
        logs_data = json.loads(logs_response.data)
        if logs_data.get('logs'):
            log_id = logs_data['logs'][0].get('id', 'test-id')
            response = client.post(f'/api/agents/execution/{log_id}/replay')
            assert response.status_code in [200, 400, 404]


class TestCollaboration:
    """Tests for collaboration workspace endpoints."""

    def test_get_threads(self, client):
        """Test listing collaboration threads."""
        response = client.get('/api/agents/collaboration/threads')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'threads' in data
        assert isinstance(data['threads'], list)

    def test_get_threads_filter_tag(self, client):
        """Test filtering threads by tag."""
        response = client.get('/api/agents/collaboration/threads?tag=research')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'threads' in data

    def test_get_threads_search(self, client):
        """Test searching threads."""
        response = client.get('/api/agents/collaboration/threads?search=test')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'threads' in data

    def test_create_thread(self, client):
        """Test creating a collaboration thread."""
        response = client.post(
            '/api/agents/collaboration/threads',
            data=json.dumps({
                'title': 'Test Thread from pytest',
                'created_by': 'test-agent',
                'tags': ['testing', 'automated']
            }),
            content_type='application/json'
        )
        assert response.status_code in [200, 201]
        data = json.loads(response.data)
        assert 'thread' in data or 'id' in data

    def test_get_thread_detail(self, client):
        """Test getting a specific thread."""
        # First get list to find a valid ID
        list_response = client.get('/api/agents/collaboration/threads')
        list_data = json.loads(list_response.data)
        if list_data.get('threads'):
            thread_id = list_data['threads'][0].get('id', 'test-id')
            response = client.get(f'/api/agents/collaboration/threads/{thread_id}')
            assert response.status_code in [200, 404]

    def test_add_message_to_thread(self, client):
        """Test adding a message to an existing thread."""
        # First get or create a thread
        list_response = client.get('/api/agents/collaboration/threads')
        list_data = json.loads(list_response.data)
        if list_data.get('threads'):
            thread_id = list_data['threads'][0].get('id', 'test-id')
            response = client.post(
                f'/api/agents/collaboration/threads/{thread_id}/messages',
                data=json.dumps({
                    'from_agent': 'test-agent',
                    'content': 'Automated test message',
                    'tags': ['test']
                }),
                content_type='application/json'
            )
            assert response.status_code in [200, 201, 404]

    def test_get_notifications(self, client):
        """Test getting user notifications."""
        response = client.get('/api/agents/notifications')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'notifications' in data
        assert isinstance(data['notifications'], list)
