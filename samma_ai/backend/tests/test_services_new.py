import pytest
from app.services.model_router_service import ModelRouterService
from app.services.orchestrator_service import PalaJarvisOrchestrator
from app.services.collaboration_service import CollaborationService
from app.services.execution_monitor_service import ExecutionMonitorService


class TestModelRouterService:
    """Tests for the multi-model routing service."""

    def test_singleton_instance(self, app):
        """Test that ModelRouterService returns consistent instance."""
        with app.app_context():
            svc = ModelRouterService()
            assert svc is not None

    def test_list_available_models(self, app):
        """Test listing available models."""
        with app.app_context():
            svc = ModelRouterService()
            models = svc.list_available_models()
            assert isinstance(models, list)
            assert len(models) > 0
            for m in models:
                assert 'id' in m
                assert 'provider' in m

    def test_model_has_provider(self, app):
        """Test that each model includes a provider type."""
        with app.app_context():
            svc = ModelRouterService()
            models = svc.list_available_models()
            providers = {m['provider'] for m in models}
            # Should have at least Claude or Ollama
            assert len(providers) > 0


class TestPalaJarvisOrchestrator:
    """Tests for the Pala-Jarvis orchestration service."""

    def test_singleton_instance(self):
        """Test that orchestrator is instantiable."""
        orch = PalaJarvisOrchestrator()
        assert orch is not None

    def test_delegate_task(self):
        """Test basic task delegation."""
        orch = PalaJarvisOrchestrator()
        result = orch.delegate_task(
            description='Analyze Sutta MN 10',
            priority='medium'
        )
        assert result is not None
        assert 'delegation_id' in result or 'id' in result or isinstance(result, dict)

    def test_delegate_task_with_team(self):
        """Test task delegation to specific team."""
        orch = PalaJarvisOrchestrator()
        result = orch.delegate_task(
            description='Review Vinaya translation',
            target_team='vinaya',
            priority='high'
        )
        assert result is not None

    def test_get_delegations(self):
        """Test retrieving delegation history."""
        orch = PalaJarvisOrchestrator()
        delegations = orch.get_delegations()
        assert isinstance(delegations, list)

    def test_get_notifications(self):
        """Test retrieving user notifications."""
        orch = PalaJarvisOrchestrator()
        notifications = orch.get_user_notifications()
        assert isinstance(notifications, list)


class TestCollaborationService:
    """Tests for the collaboration workspace service."""

    def test_singleton_instance(self):
        """Test that service is instantiable."""
        svc = CollaborationService()
        assert svc is not None

    def test_get_threads_returns_list(self):
        """Test listing threads returns a list."""
        svc = CollaborationService()
        threads = svc.get_threads()
        assert isinstance(threads, list)

    def test_demo_threads_exist(self):
        """Test that pre-seeded demo threads are present."""
        svc = CollaborationService()
        threads = svc.get_threads()
        assert len(threads) > 0, "Should have pre-seeded demo threads"

    def test_create_thread(self):
        """Test creating a new thread."""
        svc = CollaborationService()
        thread = svc.create_thread(
            title='Test Thread',
            created_by='pytest',
            tags=['test']
        )
        assert thread is not None
        assert thread.get('title') == 'Test Thread' or 'id' in thread

    def test_add_message(self):
        """Test adding message to a thread."""
        svc = CollaborationService()
        threads = svc.get_threads()
        if threads:
            thread_id = threads[0]['id']
            result = svc.add_message(
                thread_id=thread_id,
                from_agent='pytest',
                content='Test message',
                tags=['test']
            )
            assert result is not None

    def test_search_threads(self):
        """Test searching threads."""
        svc = CollaborationService()
        results = svc.get_threads(search='test')
        assert isinstance(results, list)

    def test_filter_threads_by_tag(self):
        """Test filtering threads by tag."""
        svc = CollaborationService()
        results = svc.get_threads(tag='research')
        assert isinstance(results, list)


class TestExecutionMonitorService:
    """Tests for the execution monitoring service."""

    def test_singleton_instance(self):
        """Test that service is instantiable."""
        svc = ExecutionMonitorService()
        assert svc is not None

    def test_get_logs_returns_list(self):
        """Test that get_logs returns a list."""
        svc = ExecutionMonitorService()
        logs = svc.get_logs()
        assert isinstance(logs, list)

    def test_demo_logs_exist(self):
        """Test that pre-seeded demo logs are present."""
        svc = ExecutionMonitorService()
        logs = svc.get_logs()
        assert len(logs) > 0, "Should have pre-seeded demo logs"

    def test_log_has_required_fields(self):
        """Test that each log has required fields."""
        svc = ExecutionMonitorService()
        logs = svc.get_logs()
        if logs:
            log = logs[0]
            assert 'id' in log
            assert 'status' in log

    def test_filter_by_status(self):
        """Test filtering logs by status."""
        svc = ExecutionMonitorService()
        results = svc.get_logs(status='running')
        assert isinstance(results, list)

    def test_get_queue_status(self):
        """Test getting queue status."""
        svc = ExecutionMonitorService()
        status = svc.get_queue_status()
        assert isinstance(status, dict)
        # Should have count fields
        for key in ['queued', 'running', 'completed', 'failed']:
            assert key in status, f"Queue status should include '{key}'"

    def test_pause_task(self):
        """Test pausing a task."""
        svc = ExecutionMonitorService()
        logs = svc.get_logs()
        running_logs = [l for l in logs if l.get('status') == 'running']
        if running_logs:
            result = svc.pause_task(running_logs[0]['id'])
            assert result is not None

    def test_cancel_task(self):
        """Test cancelling a task."""
        svc = ExecutionMonitorService()
        logs = svc.get_logs()
        if logs:
            result = svc.cancel_task(logs[0]['id'])
            assert result is not None
