"""
Extended unit tests for cost tracking

Tests:
- Task cost estimation accuracy
- Document cost estimation with/without context agent
- Collection cost estimation
- Budget enforcement
- Cost record tracking
- Daily/monthly cost aggregation
"""

import pytest
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from enrichment_service.utils.cost_tracker import CostTracker


class TestTaskCostEstimation:
    """Test per-task cost estimation"""

    def test_estimate_ollama_task_cost(self, cost_tracker_fixture):
        """Test Ollama task costs zero"""
        cost = cost_tracker_fixture.estimate_task_cost('extract_people')
        assert cost['model'] == 'ollama'
        assert cost['estimated_usd'] == 0.0

    def test_estimate_claude_sonnet_task_cost(self, cost_tracker_fixture):
        """Test Claude Sonnet task costs"""
        cost = cost_tracker_fixture.estimate_task_cost('generate_summary')
        assert cost['model'] == 'claude-sonnet-4'
        assert cost['estimated_usd'] > 0.0
        assert cost['input_tokens'] > 0
        assert cost['output_tokens'] > 0

    def test_estimate_claude_opus_task_cost(self, cost_tracker_fixture):
        """Test Claude Opus task costs"""
        cost = cost_tracker_fixture.estimate_task_cost('research_historical_context')
        assert cost['model'] == 'claude-opus-4-5'
        assert cost['estimated_usd'] > 0.0
        # Opus is more expensive than Sonnet
        sonnet_cost = cost_tracker_fixture.estimate_task_cost('generate_summary')
        assert cost['estimated_usd'] > sonnet_cost['estimated_usd']

    def test_unknown_task_returns_zero(self, cost_tracker_fixture):
        """Test unknown task returns zero cost"""
        cost = cost_tracker_fixture.estimate_task_cost('unknown_task')
        assert cost['estimated_usd'] == 0.0

    def test_cost_precision(self, cost_tracker_fixture):
        """Test cost precision to 6 decimal places"""
        cost = cost_tracker_fixture.estimate_task_cost('generate_summary')
        # Cost should be precise to 0.000001 USD
        assert len(str(cost['estimated_usd']).split('.')[-1]) <= 6


class TestDocumentCostEstimation:
    """Test per-document cost estimation"""

    def test_estimate_document_cost_with_context(self, cost_tracker_fixture):
        """Test document cost with context agent enabled"""
        cost = cost_tracker_fixture.estimate_document_cost(
            doc_length_chars=2000,
            enable_context_agent=True
        )
        assert cost['total_usd'] > 0
        assert cost['phase1_ollama'] == 0  # Ollama is free
        assert cost['phase2_sonnet'] > 0
        assert cost['phase3_opus'] > 0
        assert cost['total_usd'] == cost['phase1_ollama'] + cost['phase2_sonnet'] + cost['phase3_opus']

    def test_estimate_document_cost_without_context(self, cost_tracker_fixture):
        """Test document cost without context agent"""
        cost_with = cost_tracker_fixture.estimate_document_cost(
            enable_context_agent=True
        )
        cost_without = cost_tracker_fixture.estimate_document_cost(
            enable_context_agent=False
        )
        # Without context agent should be cheaper
        assert cost_without['total_usd'] < cost_with['total_usd']
        assert cost_without['phase3_opus'] == 0

    def test_document_cost_breakdown(self, cost_tracker_fixture):
        """Test cost breakdown by model"""
        cost = cost_tracker_fixture.estimate_document_cost()
        breakdown = cost['breakdown']

        assert 'ollama' in breakdown
        assert 'claude_sonnet' in breakdown
        assert 'claude_opus' in breakdown
        assert breakdown['ollama'] == 0  # Free

    def test_document_length_parameter(self, cost_tracker_fixture):
        """Test document length affects estimation"""
        short_cost = cost_tracker_fixture.estimate_document_cost(doc_length_chars=500)
        long_cost = cost_tracker_fixture.estimate_document_cost(doc_length_chars=5000)

        # Longer documents might cost more (depending on model)
        # At minimum, should track the parameter
        assert short_cost['document_length_chars'] == 500
        assert long_cost['document_length_chars'] == 5000


class TestCollectionCostEstimation:
    """Test batch/collection cost estimation"""

    def test_estimate_collection_cost_single_doc(self, cost_tracker_fixture):
        """Test collection cost for single document"""
        single_doc_cost = cost_tracker_fixture.estimate_document_cost()
        collection_cost = cost_tracker_fixture.estimate_collection_cost(num_documents=1)

        assert collection_cost['total_cost_usd'] == single_doc_cost['total_usd']

    def test_estimate_collection_cost_multiple_docs(self, cost_tracker_fixture):
        """Test collection cost scales with document count"""
        single_doc_cost = cost_tracker_fixture.estimate_document_cost()
        collection_cost = cost_tracker_fixture.estimate_collection_cost(num_documents=10)

        assert collection_cost['total_cost_usd'] == single_doc_cost['total_usd'] * 10
        assert collection_cost['num_documents'] == 10

    def test_collection_cost_breakdown(self, cost_tracker_fixture):
        """Test collection cost breakdown"""
        collection_cost = cost_tracker_fixture.estimate_collection_cost(num_documents=5)

        breakdown = collection_cost['breakdown_total']
        assert 'ollama' in breakdown
        assert 'claude_sonnet' in breakdown
        assert 'claude_opus' in breakdown
        assert breakdown['ollama'] == 0  # Free

    def test_daily_and_monthly_estimates(self, cost_tracker_fixture):
        """Test daily and monthly cost estimates"""
        collection_cost = cost_tracker_fixture.estimate_collection_cost(num_documents=100)

        # Should have daily and monthly estimates
        assert 'daily_estimate' in collection_cost
        assert 'monthly_estimate' in collection_cost
        assert collection_cost['daily_estimate'] <= collection_cost['total_cost_usd']


class TestCostRecordTracking:
    """Test recording actual API costs"""

    def test_record_api_call_success(self, cost_tracker_fixture, mock_db):
        """Test successful cost record"""
        result = cost_tracker_fixture.record_api_call(
            enrichment_job_id='job_123',
            document_id='doc_456',
            model='claude-sonnet-4',
            task_name='generate_summary',
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.005
        )

        assert result is True
        # Verify record was inserted
        record = mock_db.cost_records.find_one({'document_id': 'doc_456'})
        assert record is not None
        assert record['cost_usd'] == 0.005

    def test_record_api_call_without_db(self, mock_config):
        """Test recording without database returns False"""
        tracker = CostTracker(db=None, config=mock_config)
        result = tracker.record_api_call(
            enrichment_job_id='job_123',
            document_id='doc_456',
            model='claude-sonnet-4',
            task_name='generate_summary',
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.005
        )

        assert result is False

    def test_get_document_costs(self, cost_tracker_fixture, mock_db):
        """Test retrieving document costs"""
        # Record multiple costs for same document
        for i in range(3):
            cost_tracker_fixture.record_api_call(
                enrichment_job_id='job_123',
                document_id='doc_456',
                model='claude-sonnet-4',
                task_name=f'task_{i}',
                input_tokens=1000,
                output_tokens=500,
                cost_usd=0.005
            )

        costs = cost_tracker_fixture.get_document_costs('doc_456')
        assert costs['document_id'] == 'doc_456'
        assert costs['api_calls'] == 3
        assert costs['total_cost_usd'] == 0.015

    def test_get_job_costs(self, cost_tracker_fixture, mock_db):
        """Test retrieving job-level costs"""
        # Record costs for multiple documents in same job
        for doc_id in ['doc_1', 'doc_2', 'doc_3']:
            cost_tracker_fixture.record_api_call(
                enrichment_job_id='job_123',
                document_id=doc_id,
                model='claude-sonnet-4',
                task_name='generate_summary',
                input_tokens=1000,
                output_tokens=500,
                cost_usd=0.005
            )

        costs = cost_tracker_fixture.get_job_costs('job_123')
        assert costs['enrichment_job_id'] == 'job_123'
        assert costs['num_documents'] == 3
        assert costs['total_cost_usd'] == 0.015
        assert costs['cost_per_document'] == pytest.approx(0.005)


class TestBudgetTracking:
    """Test daily and monthly budget tracking"""

    def test_get_daily_costs(self, cost_tracker_fixture, mock_db):
        """Test daily cost aggregation"""
        today = datetime.now(timezone.utc)

        # Record costs for today
        for i in range(5):
            cost_tracker_fixture.record_api_call(
                enrichment_job_id=f'job_{i}',
                document_id=f'doc_{i}',
                model='claude-sonnet-4',
                task_name='generate_summary',
                input_tokens=1000,
                output_tokens=500,
                cost_usd=0.001
            )

        costs = cost_tracker_fixture.get_daily_costs(today)
        assert costs['total_cost_usd'] == pytest.approx(0.005)
        assert costs['api_calls'] == 5

    def test_check_daily_budget(self, cost_tracker_fixture, mock_db):
        """Test daily budget checking"""
        # Record some costs
        cost_tracker_fixture.record_api_call(
            enrichment_job_id='job_123',
            document_id='doc_456',
            model='claude-sonnet-4',
            task_name='generate_summary',
            input_tokens=1000,
            output_tokens=500,
            cost_usd=10.00
        )

        budget = cost_tracker_fixture.check_budget(time_period='daily')
        assert budget['time_period'] == 'daily'
        assert budget['spent_usd'] == 10.00
        assert budget['budget_usd'] == 100.00
        assert budget['percentage_used'] == pytest.approx(10.0)

    def test_budget_alert_threshold(self, cost_tracker_fixture, mock_db):
        """Test budget alert when threshold exceeded"""
        # Record costs above alert threshold
        cost_tracker_fixture.record_api_call(
            enrichment_job_id='job_123',
            document_id='doc_456',
            model='claude-sonnet-4',
            task_name='generate_summary',
            input_tokens=1000,
            output_tokens=500,
            cost_usd=85.00
        )

        budget = cost_tracker_fixture.check_budget(time_period='daily')
        assert budget['alert'] is not None
        assert 'WARNING' in budget['alert']

    def test_budget_exceeded(self, cost_tracker_fixture, mock_db):
        """Test critical alert when budget exceeded"""
        # Record costs exceeding budget
        cost_tracker_fixture.record_api_call(
            enrichment_job_id='job_123',
            document_id='doc_456',
            model='claude-sonnet-4',
            task_name='generate_summary',
            input_tokens=1000,
            output_tokens=500,
            cost_usd=150.00
        )

        budget = cost_tracker_fixture.check_budget(time_period='daily')
        assert budget['alert'] is not None
        assert 'CRITICAL' in budget['alert']

    def test_model_breakdown(self, cost_tracker_fixture, mock_db):
        """Test cost breakdown by model"""
        # Record costs for different models
        cost_tracker_fixture.record_api_call(
            enrichment_job_id='job_1',
            document_id='doc_1',
            model='claude-sonnet-4',
            task_name='generate_summary',
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.005
        )
        cost_tracker_fixture.record_api_call(
            enrichment_job_id='job_2',
            document_id='doc_2',
            model='claude-opus-4-5',
            task_name='research_historical_context',
            input_tokens=2000,
            output_tokens=1000,
            cost_usd=0.050
        )

        budget = cost_tracker_fixture.check_budget(time_period='daily')
        breakdown = budget['breakdown']
        assert 'claude-sonnet-4' in breakdown
        assert 'claude-opus-4-5' in breakdown


class TestCostTrackerEdgeCases:
    """Test edge cases and error conditions"""

    def test_zero_token_cost(self, cost_tracker_fixture):
        """Test task with zero tokens"""
        cost = cost_tracker_fixture.estimate_task_cost('extract_people')
        assert cost['estimated_usd'] == 0.0

    def test_large_document_cost(self, cost_tracker_fixture):
        """Test very large document cost estimation"""
        cost = cost_tracker_fixture.estimate_document_cost(doc_length_chars=100000)
        assert cost['total_usd'] > 0
        assert cost['document_length_chars'] == 100000

    def test_empty_costs_retrieval(self, cost_tracker_fixture):
        """Test retrieving costs when no records exist"""
        costs = cost_tracker_fixture.get_document_costs('nonexistent_doc')
        assert costs.get('document_id') == 'nonexistent_doc'
        assert costs.get('api_calls') == 0 or 'api_calls' not in costs
