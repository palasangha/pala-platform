"""
Unit tests for cost tracking and budget management

Tests CostTracker, BudgetManager, and cost-related functionality
"""

import pytest
from datetime import datetime, timedelta
from enrichment_service.utils.cost_tracker import CostTracker
from enrichment_service.utils.budget_manager import BudgetManager


class TestCostTracker:
    """Test CostTracker functionality"""

    @pytest.mark.unit
    def test_estimate_task_cost(self, cost_tracker_fixture):
        """Test task cost estimation"""
        # Test known task
        estimate = cost_tracker_fixture.estimate_task_cost('generate_summary')

        assert 'estimated_usd' in estimate
        assert estimate['estimated_usd'] > 0
        assert estimate['model'] == 'claude-sonnet-4'
        assert 'input_tokens' in estimate
        assert 'output_tokens' in estimate

    @pytest.mark.unit
    def test_estimate_task_cost_unknown(self, cost_tracker_fixture):
        """Test estimation for unknown task"""
        estimate = cost_tracker_fixture.estimate_task_cost('unknown_task')

        assert estimate['estimated_usd'] == 0.0
        assert estimate['model'] == 'unknown'

    @pytest.mark.unit
    def test_estimate_document_cost(self, cost_tracker_fixture):
        """Test document-level cost estimation"""
        # With context agent enabled
        estimate = cost_tracker_fixture.estimate_document_cost(
            doc_length_chars=2000,
            enable_context_agent=True
        )

        assert 'total_usd' in estimate
        assert estimate['total_usd'] > 0
        assert estimate['phase1_ollama'] == 0.0  # Ollama is free
        assert estimate['phase2_sonnet'] > 0
        assert estimate['phase3_opus'] > 0

    @pytest.mark.unit
    def test_estimate_document_cost_no_context(self, cost_tracker_fixture):
        """Test document cost without context agent"""
        estimate_with = cost_tracker_fixture.estimate_document_cost(
            doc_length_chars=2000,
            enable_context_agent=True
        )
        estimate_without = cost_tracker_fixture.estimate_document_cost(
            doc_length_chars=2000,
            enable_context_agent=False
        )

        # Without context should be cheaper
        assert estimate_without['total_usd'] < estimate_with['total_usd']
        assert estimate_without['phase3_opus'] == 0.0

    @pytest.mark.unit
    def test_estimate_collection_cost(self, cost_tracker_fixture):
        """Test collection-level cost estimation"""
        estimate = cost_tracker_fixture.estimate_collection_cost(
            num_documents=100,
            avg_doc_length=2000,
            enable_context_agent=True
        )

        assert estimate['num_documents'] == 100
        assert estimate['cost_per_document'] > 0
        assert estimate['total_cost_usd'] == estimate['cost_per_document'] * 100

    @pytest.mark.unit
    def test_record_api_call(self, cost_tracker_fixture, mock_db):
        """Test recording API call"""
        success = cost_tracker_fixture.record_api_call(
            enrichment_job_id='job_123',
            document_id='doc_456',
            model='claude-sonnet-4',
            task_name='generate_summary',
            input_tokens=1200,
            output_tokens=400,
            cost_usd=0.045
        )

        assert success is True

        # Verify record was saved
        record = mock_db.cost_records.find_one({'document_id': 'doc_456'})
        assert record is not None
        assert record['cost_usd'] == 0.045
        assert record['total_tokens'] == 1600

    @pytest.mark.unit
    def test_get_document_costs(self, cost_tracker_fixture, mock_db):
        """Test retrieving document costs"""
        # Record multiple calls for a document
        for i in range(3):
            cost_tracker_fixture.record_api_call(
                enrichment_job_id='job_123',
                document_id='doc_789',
                model='claude-sonnet-4',
                task_name=f'task_{i}',
                input_tokens=1000,
                output_tokens=300,
                cost_usd=0.040
            )

        costs = cost_tracker_fixture.get_document_costs('doc_789')

        assert costs['document_id'] == 'doc_789'
        assert costs['total_cost_usd'] == pytest.approx(0.120, rel=1e-2)
        assert costs['api_calls'] == 3

    @pytest.mark.unit
    def test_get_job_costs(self, cost_tracker_fixture, mock_db):
        """Test retrieving job costs"""
        # Record costs for multiple documents in a job
        for doc_id in ['doc_1', 'doc_2', 'doc_3']:
            cost_tracker_fixture.record_api_call(
                enrichment_job_id='job_xyz',
                document_id=doc_id,
                model='claude-opus-4-5',
                task_name='research_historical_context',
                input_tokens=2500,
                output_tokens=1500,
                cost_usd=0.140
            )

        costs = cost_tracker_fixture.get_job_costs('job_xyz')

        assert costs['enrichment_job_id'] == 'job_xyz'
        assert costs['num_documents'] == 3
        assert costs['total_cost_usd'] == pytest.approx(0.420, rel=1e-2)
        assert costs['cost_per_document'] == pytest.approx(0.140, rel=1e-2)


class TestBudgetManager:
    """Test BudgetManager functionality"""

    @pytest.mark.unit
    def test_can_afford_task(self, budget_manager_fixture, mock_db):
        """Test if we can afford a task"""
        # Initially should be able to afford tasks
        can_afford = budget_manager_fixture.can_afford_task('generate_summary')

        assert can_afford is True

    @pytest.mark.unit
    def test_get_enrichment_config(self, budget_manager_fixture):
        """Test getting enrichment configuration based on budget"""
        config = budget_manager_fixture.get_enrichment_config()

        assert 'enable_ollama' in config
        assert 'enable_claude_sonnet' in config
        assert 'enable_claude_opus' in config
        assert config['enable_ollama'] is True  # Always enabled

    @pytest.mark.unit
    def test_should_enable_context_agent_within_budget(self, budget_manager_fixture):
        """Test context agent is enabled when within budget"""
        should_enable = budget_manager_fixture.should_enable_context_agent()

        # Should be enabled initially (no spending)
        assert should_enable is True

    @pytest.mark.unit
    def test_should_disable_context_agent_high_spend(self, budget_manager_fixture, mock_db, mock_config):
        """Test context agent is disabled at high spend"""
        # Manually set daily spend to 85% of budget
        daily_budget = mock_config['DAILY_BUDGET_USD']
        high_spend = daily_budget * 0.85

        # Record costs to reach 85% budget
        cost_tracker = CostTracker(mock_db, mock_config)
        for i in range(int(high_spend / 0.14)):  # ~6 Opus calls at $0.14 each
            cost_tracker.record_api_call(
                enrichment_job_id='job_test',
                document_id=f'doc_{i}',
                model='claude-opus-4-5',
                task_name='research_historical_context',
                input_tokens=2500,
                output_tokens=1500,
                cost_usd=0.140
            )

        should_enable = budget_manager_fixture.should_enable_context_agent()

        # Should be disabled at >80% spend
        assert should_enable is False

    @pytest.mark.unit
    def test_can_process_document(self, budget_manager_fixture):
        """Test if we can process a document"""
        can_process, reason = budget_manager_fixture.can_process_document(doc_length_chars=2000)

        assert can_process is True
        assert reason is None

    @pytest.mark.unit
    def test_get_recommendations(self, budget_manager_fixture):
        """Test getting cost optimization recommendations"""
        recommendations = budget_manager_fixture.get_recommendations()

        assert 'daily_status' in recommendations
        assert 'monthly_status' in recommendations
        assert 'actions' in recommendations

    @pytest.mark.unit
    def test_check_budget(self, budget_manager_fixture):
        """Test budget checking"""
        daily_budget = budget_manager_fixture.check_budget('daily')

        assert 'budget_usd' in daily_budget
        assert 'spent_usd' in daily_budget
        assert 'remaining_usd' in daily_budget
        assert 'percentage_used' in daily_budget

    @pytest.mark.unit
    def test_budget_report_generation(self, budget_manager_fixture):
        """Test budget report generation"""
        report = budget_manager_fixture.create_budget_report()

        assert 'BUDGET REPORT' in report
        assert 'DAILY BUDGET' in report
        assert 'MONTHLY BUDGET' in report
        assert '$' in report  # Should contain currency


class TestCostAnalysis:
    """Test cost analysis scenarios"""

    @pytest.mark.unit
    def test_cost_per_document_calculation(self, cost_tracker_fixture, mock_db):
        """Test calculating cost per document"""
        # Record enrichment with multiple agent calls
        agents = [
            ('metadata-agent', 'extract_document_type', 0.001),
            ('entity-agent', 'extract_people', 0.002),
            ('content-agent', 'generate_summary', 0.045),
            ('context-agent', 'research_historical_context', 0.140)
        ]

        total_cost = 0.0
        for agent, task, cost in agents:
            cost_tracker_fixture.record_api_call(
                enrichment_job_id='job_analysis',
                document_id='doc_analysis',
                model='claude' if cost > 0.01 else 'ollama',
                task_name=task,
                input_tokens=1000,
                output_tokens=500,
                cost_usd=cost
            )
            total_cost += cost

        costs = cost_tracker_fixture.get_document_costs('doc_analysis')

        assert costs['total_cost_usd'] == pytest.approx(total_cost, rel=1e-2)
        assert costs['api_calls'] == 4

    @pytest.mark.unit
    def test_cost_breakdown_by_model(self, cost_tracker_fixture, mock_db):
        """Test cost breakdown by model"""
        # Record calls for different models
        cost_tracker_fixture.record_api_call(
            enrichment_job_id='job_breakdown',
            document_id='doc_breakdown',
            model='claude-sonnet-4',
            task_name='summary',
            input_tokens=1200,
            output_tokens=400,
            cost_usd=0.045
        )

        cost_tracker_fixture.record_api_call(
            enrichment_job_id='job_breakdown',
            document_id='doc_breakdown',
            model='claude-opus-4-5',
            task_name='context',
            input_tokens=2500,
            output_tokens=1500,
            cost_usd=0.140
        )

        costs = cost_tracker_fixture.get_document_costs('doc_breakdown')
        breakdown = costs['breakdown_by_model']

        assert 'claude-sonnet-4' in breakdown
        assert 'claude-opus-4-5' in breakdown
        assert breakdown['claude-sonnet-4']['cost'] == pytest.approx(0.045, rel=1e-2)
        assert breakdown['claude-opus-4-5']['cost'] == pytest.approx(0.140, rel=1e-2)

    @pytest.mark.unit
    def test_estimated_vs_actual_cost(self, cost_tracker_fixture):
        """Test estimation accuracy"""
        # Estimate for document
        estimated = cost_tracker_fixture.estimate_document_cost(
            doc_length_chars=2000,
            enable_context_agent=True
        )

        # Typical Claude usage costs
        typical_total = estimated['total_usd']

        # Should be in reasonable range ($0.15-0.40)
        assert 0.15 < typical_total < 0.40

    @pytest.mark.unit
    @pytest.mark.parametrize("doc_length,expected_range", [
        (1000, (0.10, 0.35)),
        (2000, (0.15, 0.40)),
        (5000, (0.20, 0.45))
    ])
    def test_cost_by_document_length(self, cost_tracker_fixture, doc_length, expected_range):
        """Test cost estimation for various document lengths"""
        estimate = cost_tracker_fixture.estimate_document_cost(
            doc_length_chars=doc_length,
            enable_context_agent=True
        )

        assert expected_range[0] < estimate['total_usd'] < expected_range[1]


class TestBudgetConstraints:
    """Test budget constraint enforcement"""

    @pytest.mark.unit
    def test_daily_budget_limit(self, budget_manager_fixture, mock_db, mock_config):
        """Test daily budget limit enforcement"""
        # Simulate spending at limit
        daily_limit = mock_config['DAILY_BUDGET_USD']

        # Mock spending
        cost_tracker = CostTracker(mock_db, mock_config)

        # Record enough to reach budget
        for i in range(10):
            cost_tracker.record_api_call(
                enrichment_job_id='job_limit',
                document_id=f'doc_{i}',
                model='claude-opus-4-5',
                task_name='research_historical_context',
                input_tokens=2500,
                output_tokens=1500,
                cost_usd=10.0  # $10 per call
            )

        # Check if budget is exceeded
        is_exceeded = budget_manager_fixture.is_daily_budget_exceeded()
        assert is_exceeded is True

    @pytest.mark.unit
    def test_per_document_cost_limit(self, budget_manager_fixture, mock_config):
        """Test per-document cost limit"""
        max_cost = mock_config['MAX_COST_PER_DOC']

        # Document that would exceed limit
        estimate = budget_manager_fixture.budget_manager.cost_tracker.estimate_document_cost(
            doc_length_chars=10000,  # Very long document
            enable_context_agent=True
        )

        # Even long documents shouldn't exceed per-doc limit
        assert estimate['total_usd'] <= max_cost * 2  # Allow some variance


@pytest.mark.unit
class TestMetricsIntegration:
    """Test metrics recording with cost tracking"""

    def test_cost_tracking_with_metrics(self, cost_tracker_fixture, mock_db):
        """Test that metrics can be recorded alongside costs"""
        # Record cost
        cost_tracker_fixture.record_api_call(
            enrichment_job_id='job_metrics',
            document_id='doc_metrics',
            model='claude-sonnet-4',
            task_name='generate_summary',
            input_tokens=1200,
            output_tokens=400,
            cost_usd=0.045
        )

        # Verify it was recorded
        costs = cost_tracker_fixture.get_document_costs('doc_metrics')
        assert costs['total_cost_usd'] > 0
