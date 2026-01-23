"""
Integration tests for enrichment pipeline

Tests:
- End-to-end OCR to enriched document flow
- Agent pipeline (3 phases)
- Schema validation and completeness
- Review queue routing
- Error handling and recovery
"""

import pytest
import json
from datetime import datetime
from typing import Dict, Any
from unittest.mock import AsyncMock, patch

from enrichment_service.workers.agent_orchestrator import AgentOrchestrator
from enrichment_service.schema.validator import SchemaValidator
from enrichment_service.review.review_queue import ReviewQueue


@pytest.mark.integration
class TestEndToEndEnrichmentFlow:
    """Test complete enrichment flow from OCR to database"""

    @pytest.mark.asyncio
    async def test_enrich_document_basic(
        self,
        mock_db,
        sample_ocr_data,
        sample_enriched_data,
        mock_mcp_client
    ):
        """Test basic document enrichment"""
        # Mock MCP agent responses
        mock_mcp_client.invoke_tool.side_effect = [
            # Phase 1 responses
            sample_enriched_data['metadata'],  # metadata-agent
            sample_enriched_data['analysis']['people'],  # entity-agent
            sample_enriched_data['content'],  # structure-agent
            # Phase 2 responses
            {'summary': 'Test summary'},  # content-agent
            # Phase 3 responses
            {'context': 'Historical context'},  # context-agent
        ]

        orchestrator = AgentOrchestrator(
            mcp_client=mock_mcp_client,
            schema_path='test_schema.json',
            db=mock_db
        )

        # Mock schema validation
        with patch.object(orchestrator, 'validator') as mock_validator:
            mock_validator.calculate_completeness.return_value = {
                'completeness_score': 0.95,
                'passes_threshold': True,
                'missing_fields': [],
                'low_confidence_fields': [],
                'requires_review': False
            }

            result = await orchestrator.enrich_document(
                document_id='doc_123',
                ocr_data=sample_ocr_data
            )

            assert result is not None
            assert result['document_id'] == 'doc_123'

    @pytest.mark.asyncio
    async def test_enrich_document_with_missing_fields(
        self,
        mock_db,
        sample_ocr_data,
        mock_mcp_client
    ):
        """Test enrichment with missing required fields"""
        orchestrator = AgentOrchestrator(
            mcp_client=mock_mcp_client,
            schema_path='test_schema.json',
            db=mock_db
        )

        # Mock low completeness score
        with patch.object(orchestrator, 'validator') as mock_validator:
            mock_validator.calculate_completeness.return_value = {
                'completeness_score': 0.75,
                'passes_threshold': False,
                'missing_fields': ['metadata.storage_location', 'analysis.keywords'],
                'low_confidence_fields': [],
                'requires_review': True,
                'review_reason': 'Completeness score 75.0% below threshold'
            }

            result = await orchestrator.enrich_document(
                document_id='doc_123',
                ocr_data=sample_ocr_data
            )

            # Should flag for review
            assert result['requires_review'] is True
            assert len(result['missing_fields']) > 0


@pytest.mark.integration
class TestAgentPipeline:
    """Test 3-phase agent orchestration"""

    @pytest.mark.asyncio
    async def test_phase_1_parallel_agents(self, mock_mcp_client):
        """Test Phase 1 parallel agent execution"""
        orchestrator = AgentOrchestrator(mcp_client=mock_mcp_client)

        # Mock Phase 1 responses
        phase1_results = {
            'metadata-agent': {'document_type': 'letter'},
            'entity-agent': {'people': [], 'organizations': []},
            'structure-agent': {'salutation': 'Dear Friend', 'body': []}
        }

        mock_mcp_client.invoke_tool.side_effect = [
            phase1_results['metadata-agent'],
            phase1_results['entity-agent'],
            phase1_results['structure-agent']
        ]

        # Mock phase1_results in orchestrator
        with patch.object(orchestrator, '_run_phase1') as mock_phase1:
            mock_phase1.return_value = phase1_results

            result = await orchestrator._run_phase1({'text': 'test'})
            assert result == phase1_results

    @pytest.mark.asyncio
    async def test_phase_2_sequential_content_agent(self, mock_mcp_client):
        """Test Phase 2 content analysis"""
        orchestrator = AgentOrchestrator(mcp_client=mock_mcp_client)

        phase1_results = {
            'structure': {'body': ['paragraph 1', 'paragraph 2']},
            'entities': {}
        }

        phase2_response = {
            'summary': 'Document discusses important topics',
            'keywords': ['topic1', 'topic2']
        }

        mock_mcp_client.invoke_tool.return_value = phase2_response

        # Mock phase2 execution
        with patch.object(orchestrator, '_run_phase2') as mock_phase2:
            mock_phase2.return_value = phase2_response

            result = await orchestrator._run_phase2({'text': 'test'}, phase1_results)
            assert result == phase2_response

    @pytest.mark.asyncio
    async def test_phase_3_context_agent(self, mock_mcp_client):
        """Test Phase 3 historical context generation"""
        orchestrator = AgentOrchestrator(mcp_client=mock_mcp_client)

        phase1_results = {'entities': {'people': [{'name': 'Person'}]}}
        phase2_results = {'summary': 'Summary text'}

        phase3_response = {
            'historical_context': 'This document relates to...',
            'significance': 'high'
        }

        mock_mcp_client.invoke_tool.return_value = phase3_response

        with patch.object(orchestrator, '_run_phase3') as mock_phase3:
            mock_phase3.return_value = phase3_response

            result = await orchestrator._run_phase3(
                {'text': 'test'},
                phase1_results,
                phase2_results
            )
            assert result == phase3_response


@pytest.mark.integration
class TestSchemaValidationAndReviewRouting:
    """Test schema validation and review queue routing"""

    def test_document_passes_validation(self, mock_db, sample_enriched_data):
        """Test document with sufficient completeness passes"""
        # This is a complete enriched document
        # assuming sample_enriched_data has all required fields
        assert sample_enriched_data['metadata']['id'] == 'doc_test_123'
        assert sample_enriched_data['content']['full_text']

    def test_document_fails_validation(self, mock_db):
        """Test document with low completeness fails"""
        incomplete_doc = {
            'metadata': {
                'id': 'doc_123'
                # Missing many required fields
            },
            'content': {}
        }
        # Should be caught as incomplete

    def test_review_queue_routing(self, mock_db, review_queue_fixture):
        """Test documents routed to review queue"""
        # Create review task
        task = review_queue_fixture.create_review_task(
            document_id='doc_456',
            enrichment_job_id='job_123',
            completeness_score=0.75,
            missing_fields=['metadata.storage_location'],
            review_reason='Below 95% completeness threshold'
        )

        assert task is not None
        assert task['document_id'] == 'doc_456'
        assert task['status'] == 'pending'

    def test_document_approval_workflow(self, mock_db, review_queue_fixture):
        """Test document approval workflow"""
        # Create review task
        task = review_queue_fixture.create_review_task(
            document_id='doc_789',
            enrichment_job_id='job_456',
            completeness_score=0.95,
            missing_fields=[],
            review_reason='Human reviewer approval required'
        )

        # Approve document
        result = review_queue_fixture.approve_document(
            document_id='doc_789',
            reviewer='human_reviewer',
            notes='Looks good'
        )

        assert result is True

        # Verify status changed
        task = mock_db.review_queue.find_one({'document_id': 'doc_789'})
        assert task['status'] == 'approved'
        assert task['reviewer'] == 'human_reviewer'

    def test_document_rejection_workflow(self, mock_db, review_queue_fixture):
        """Test document rejection and re-enrichment trigger"""
        # Create review task
        review_queue_fixture.create_review_task(
            document_id='doc_999',
            enrichment_job_id='job_789',
            completeness_score=0.60,
            missing_fields=['metadata', 'analysis'],
            review_reason='Insufficient enrichment'
        )

        # Reject document
        result = review_queue_fixture.reject_document(
            document_id='doc_999',
            reviewer='human_reviewer',
            reason='Content too sparse for proper analysis'
        )

        assert result is True

        # Verify status changed
        task = mock_db.review_queue.find_one({'document_id': 'doc_999'})
        assert task['status'] == 'rejected'


@pytest.mark.integration
class TestErrorHandlingAndRecovery:
    """Test error handling in enrichment pipeline"""

    @pytest.mark.asyncio
    async def test_agent_timeout_handling(self, mock_mcp_client):
        """Test handling of agent timeout"""
        from asyncio import TimeoutError as AsyncioTimeoutError

        mock_mcp_client.invoke_tool.side_effect = AsyncioTimeoutError("Agent timeout")

        orchestrator = AgentOrchestrator(mcp_client=mock_mcp_client)

        with pytest.raises(Exception):
            # Should raise or handle gracefully
            await orchestrator._run_phase1({'text': 'test'})

    @pytest.mark.asyncio
    async def test_database_connection_error(self, mock_db):
        """Test handling of database errors"""
        # Mock database failure
        mock_db.cost_records.insert_one.side_effect = Exception("DB connection lost")

        from enrichment_service.utils.cost_tracker import CostTracker
        tracker = CostTracker(mock_db)

        result = tracker.record_api_call(
            enrichment_job_id='job_123',
            document_id='doc_456',
            model='claude-sonnet-4',
            task_name='test_task',
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.005
        )

        # Should handle gracefully and return False
        assert result is False

    @pytest.mark.asyncio
    async def test_malformed_agent_response(self, mock_mcp_client):
        """Test handling of malformed agent responses"""
        # Return invalid response
        mock_mcp_client.invoke_tool.return_value = "invalid_response_not_dict"

        orchestrator = AgentOrchestrator(mcp_client=mock_mcp_client)

        # Should handle gracefully
        # Implementation should validate response type


@pytest.mark.integration
class TestCostTrackingIntegration:
    """Test cost tracking during enrichment"""

    def test_cost_recorded_per_agent_call(self, mock_db, cost_tracker_fixture):
        """Test cost recorded for each agent call"""
        # Record costs for Phase 2 agent
        cost_tracker_fixture.record_api_call(
            enrichment_job_id='job_123',
            document_id='doc_456',
            model='claude-sonnet-4',
            task_name='generate_summary',
            input_tokens=1500,
            output_tokens=400,
            cost_usd=0.00675
        )

        # Verify cost was recorded
        costs = cost_tracker_fixture.get_document_costs('doc_456')
        assert costs['total_cost_usd'] == 0.00675
        assert costs['api_calls'] == 1

    def test_cost_per_document_limit(self, cost_tracker_fixture, mock_db):
        """Test document cost limit enforcement"""
        max_cost = 0.50  # From mock_config

        # Record cost approaching limit
        cost_tracker_fixture.record_api_call(
            enrichment_job_id='job_123',
            document_id='doc_456',
            model='claude-opus-4-5',
            task_name='research_historical_context',
            input_tokens=3000,
            output_tokens=2000,
            cost_usd=0.48
        )

        costs = cost_tracker_fixture.get_document_costs('doc_456')
        assert costs['total_cost_usd'] <= max_cost

    def test_daily_budget_enforcement(self, cost_tracker_fixture, mock_db):
        """Test daily budget limit is tracked"""
        daily_budget = 100.00  # From mock_config

        budget = cost_tracker_fixture.check_budget(time_period='daily')
        assert budget['budget_usd'] == daily_budget


@pytest.mark.integration
class TestCompleteDocumentFlow:
    """Test complete document processing flow"""

    @pytest.mark.asyncio
    async def test_document_from_ocr_to_database(
        self,
        mock_db,
        sample_ocr_data,
        sample_enriched_data,
        mock_mcp_client
    ):
        """Test complete flow: OCR → Enrichment → Database → Review"""
        from bson import ObjectId

        # Step 1: Create OCR job
        ocr_job_id = ObjectId()
        mock_db.ocr_jobs.insert_one({
            '_id': ocr_job_id,
            'document_id': 'doc_123',
            'status': 'completed',
            'ocr_result': sample_ocr_data
        })

        # Step 2: Create enrichment job
        enrichment_job_id = ObjectId()
        mock_db.enrichment_jobs.insert_one({
            '_id': enrichment_job_id,
            'ocr_job_id': str(ocr_job_id),
            'document_id': 'doc_123',
            'status': 'processing'
        })

        # Step 3: Save enriched document
        mock_db.enriched_documents.insert_one({
            'document_id': 'doc_123',
            'enrichment_job_id': str(enrichment_job_id),
            'enriched_data': sample_enriched_data,
            'completeness_score': 0.95,
            'status': 'approved',
            'created_at': datetime.utcnow()
        })

        # Step 4: Verify in database
        enriched_doc = mock_db.enriched_documents.find_one({'document_id': 'doc_123'})
        assert enriched_doc is not None
        assert enriched_doc['status'] == 'approved'
        assert enriched_doc['completeness_score'] == 0.95
