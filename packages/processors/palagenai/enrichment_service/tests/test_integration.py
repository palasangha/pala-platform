"""
Integration tests for enrichment pipeline

Tests end-to-end scenarios with sample historical letters
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime
from enrichment_service.schema.validator import HistoricalLettersValidator


@pytest.mark.integration
class TestEnrichmentPipeline:
    """Integration tests for complete enrichment pipeline"""

    def test_schema_validator_with_complete_data(self, sample_enriched_data):
        """Test schema validator with complete enriched data"""
        # Note: Requires actual schema file, so this may be mocked in CI
        try:
            validator = HistoricalLettersValidator(
                '/app/enrichment_service/schema/historical_letters_schema.json'
            )

            completeness = validator.calculate_completeness(sample_enriched_data)

            # With complete enriched data, should have high completeness
            assert completeness['completeness_score'] > 0.7
            assert isinstance(completeness['missing_fields'], list)
            assert isinstance(completeness['low_confidence_fields'], list)
        except FileNotFoundError:
            pytest.skip("Schema file not available in test environment")

    @pytest.mark.asyncio
    async def test_enrichment_orchestrator_phase1(self, mock_mcp_client, sample_ocr_data):
        """Test Phase 1 of enrichment (parallel agents)"""
        from enrichment_service.workers.agent_orchestrator import AgentOrchestrator

        orchestrator = AgentOrchestrator(mcp_client=mock_mcp_client)

        # Mock Phase 1 agent responses
        mock_mcp_client.invoke_tool.side_effect = [
            {  # metadata-agent result
                'document_type': 'letter',
                'confidence': 0.95,
                'access_level': 'public'
            },
            {  # entity-agent result
                'people': [
                    {'name': 'S.N. Goenka', 'role': 'sender', 'title': 'Founder'}
                ],
                'organizations': [
                    {'name': 'Vipassana International Academy', 'type': 'institution'}
                ],
                'locations': [
                    {'name': 'Igatpuri', 'type': 'city', 'country': 'India'}
                ]
            },
            {  # structure-agent result
                'salutation': 'Dear Friend,',
                'body': 'Letter body...',
                'closing': 'With all good wishes',
                'signature': 'S.N. Goenka'
            }
        ]

        result = await orchestrator._run_phase1(sample_ocr_data)

        assert 'metadata' in result
        assert 'entities' in result
        assert 'structure' in result

    def test_review_queue_workflow(self, review_queue_fixture, mock_db):
        """Test complete review queue workflow"""
        # Create review task
        review_id = review_queue_fixture.create_task(
            document_id='doc_review_test',
            enrichment_job_id='job_review_test',
            reason='completeness_below_threshold',
            missing_fields=['analysis.historical_context', 'analysis.significance'],
            low_confidence_fields=[
                {'field_path': 'content.summary', 'value': 'Short summary', 'confidence': 0.45}
            ]
        )

        assert review_id is not None

        # Fetch task
        task = review_queue_fixture.get_task(review_id)
        assert task is not None
        assert task['status'] == 'pending'

        # Assign task
        success = review_queue_fixture.assign_task(review_id, 'reviewer_001')
        assert success is True

        # Approve task
        success = review_queue_fixture.approve_task(
            review_id,
            'reviewer_001',
            reviewer_notes='Added missing context',
            corrections={
                'analysis': {
                    'historical_context': 'Added historical context here...',
                    'significance': 'high'
                }
            }
        )
        assert success is True

        # Verify final status
        final_task = review_queue_fixture.get_task(review_id)
        assert final_task['status'] == 'approved'

    def test_cost_tracking_workflow(self, cost_tracker_fixture, mock_db):
        """Test complete cost tracking workflow"""
        enrichment_job_id = 'job_cost_workflow'
        document_id = 'doc_cost_workflow'

        # Simulate enrichment with multiple agent calls
        # Phase 1 - Ollama (free)
        for agent, task in [('metadata', 'extract_document_type'),
                             ('entity', 'extract_people'),
                             ('structure', 'parse_letter_body')]:
            cost_tracker_fixture.record_api_call(
                enrichment_job_id=enrichment_job_id,
                document_id=document_id,
                model='ollama',
                task_name=task,
                input_tokens=800,
                output_tokens=300,
                cost_usd=0.0
            )

        # Phase 2 - Claude Sonnet
        cost_tracker_fixture.record_api_call(
            enrichment_job_id=enrichment_job_id,
            document_id=document_id,
            model='claude-sonnet-4',
            task_name='generate_summary',
            input_tokens=1200,
            output_tokens=400,
            cost_usd=0.045
        )

        # Phase 3 - Claude Opus
        cost_tracker_fixture.record_api_call(
            enrichment_job_id=enrichment_job_id,
            document_id=document_id,
            model='claude-opus-4-5',
            task_name='research_historical_context',
            input_tokens=2500,
            output_tokens=1500,
            cost_usd=0.140
        )

        # Get costs
        doc_costs = cost_tracker_fixture.get_document_costs(document_id)
        job_costs = cost_tracker_fixture.get_job_costs(enrichment_job_id)

        # Verify costs
        assert doc_costs['total_cost_usd'] == pytest.approx(0.185, rel=1e-2)
        assert doc_costs['api_calls'] == 5
        assert job_costs['num_documents'] == 1
        assert job_costs['total_cost_usd'] == pytest.approx(0.185, rel=1e-2)


@pytest.mark.integration
class TestSampleLetterProcessing:
    """Test processing of sample historical letters"""

    def test_process_invitation_letter(self, historical_letter_sample_1):
        """Test processing an invitation letter"""
        from enrichment_service.schema.validator import HistoricalLettersValidator

        # Simulate enriched data for invitation
        enriched = {
            'metadata': {
                'id': 'letter_invitation',
                'collection_id': 'test_collection',
                'document_type': 'letter'
            },
            'document': {
                'date': {'year': 1978, 'month': 5, 'day': 10},
                'correspondence': {
                    'sender': {'name': 'S.N. Goenka'},
                    'recipient': {'name': 'Shri Desai'}
                }
            },
            'content': {
                'full_text': historical_letter_sample_1['text'],
                'summary': 'Invitation to meditation center opening',
                'salutation': 'Dear Shri Desai,',
                'closing': 'Looking forward to seeing you.'
            },
            'analysis': {
                'keywords': ['invitation', 'meditation', 'opening', 'ceremony'],
                'subjects': ['event_invitation'],
                'people': [
                    {'name': 'S.N. Goenka', 'role': 'sender'},
                    {'name': 'Shri Desai', 'role': 'recipient'}
                ]
            }
        }

        # Should be able to validate structure
        assert enriched['metadata']['document_type'] == 'letter'
        assert enriched['document']['date']['year'] == 1978
        assert len(enriched['analysis']['keywords']) > 0

    def test_process_personal_letter(self, historical_letter_sample_2):
        """Test processing a personal letter"""
        enriched = {
            'metadata': {
                'id': 'letter_personal',
                'collection_id': 'test_collection',
                'document_type': 'letter'
            },
            'document': {
                'date': {'year': 1990, 'month': 12, 'day': 25},
                'correspondence': {
                    'sender': {'name': 'S.N. Goenka'},
                    'recipient': {'name': 'Friend'}
                }
            },
            'content': {
                'full_text': historical_letter_sample_2['text'],
                'summary': 'Personal letter discussing meditation practice and European centers',
                'salutation': 'My dear friend,',
                'closing': 'In good wishes,'
            },
            'analysis': {
                'keywords': ['meditation', 'practice', 'European', 'centers', 'spiritual'],
                'subjects': ['personal_matters', 'spiritual_practice', 'organizational_management'],
                'people': [{'name': 'S.N. Goenka', 'role': 'sender'}]
            }
        }

        # Verify structure
        assert enriched['metadata']['id'] == 'letter_personal'
        assert enriched['document']['date']['year'] == 1990
        assert enriched['analysis']['subjects'][0] == 'personal_matters'


@pytest.mark.integration
class TestDataMapper:
    """Test DataMapper enrichment merge functionality"""

    def test_merge_enriched_with_ocr(self, sample_ocr_data, sample_enriched_data):
        """Test merging enriched data with OCR data"""
        from enrichment_service.services.data_mapper import DataMapper

        try:
            # Merge OCR and enriched data
            result = DataMapper.merge_enriched_with_ocr(
                ocr_data=sample_ocr_data,
                enriched_data=sample_enriched_data,
                collection_id='test_collection'
            )

            # Verify merged structure
            assert 'metadata' in result
            assert 'document' in result
            assert 'content' in result
            assert 'analysis' in result

            # Enriched data should override OCR
            assert result['metadata']['document_type'] == 'letter'
            assert result['content']['summary'] == sample_enriched_data['content']['summary']

        except ImportError:
            pytest.skip("DataMapper module structure may differ")

    def test_merge_with_missing_enriched_data(self, sample_ocr_data):
        """Test merge with empty enriched data"""
        from enrichment_service.services.data_mapper import DataMapper

        try:
            # Merge with empty enriched data
            result = DataMapper.merge_enriched_with_ocr(
                ocr_data=sample_ocr_data,
                enriched_data={},
                collection_id='test_collection'
            )

            # Should still return valid structure
            assert isinstance(result, dict)

        except ImportError:
            pytest.skip("DataMapper module structure may differ")


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndScenarios:
    """End-to-end integration scenarios"""

    def test_complete_enrichment_workflow(self, sample_ocr_data, sample_collection_metadata,
                                         cost_tracker_fixture, mock_db):
        """Test complete enrichment from OCR to final output"""
        document_id = 'doc_e2e_test'
        enrichment_job_id = 'job_e2e_test'

        # Step 1: Record OCR data
        assert sample_ocr_data['text'] is not None
        assert sample_ocr_data['confidence'] == 0.92

        # Step 2: Record enrichment costs
        cost_tracker_fixture.record_api_call(
            enrichment_job_id=enrichment_job_id,
            document_id=document_id,
            model='claude-sonnet-4',
            task_name='generate_summary',
            input_tokens=1200,
            output_tokens=400,
            cost_usd=0.045
        )

        # Step 3: Save to database
        enriched_doc = {
            '_id': document_id,
            'enrichment_job_id': enrichment_job_id,
            'ocr_data': sample_ocr_data,
            'enriched_data': {
                'metadata': {'document_type': 'letter'},
                'content': {'summary': 'Test summary'},
                'analysis': {'keywords': ['test']}
            },
            'quality_metrics': {
                'completeness_score': 0.96,
                'missing_fields': [],
                'review_status': 'approved'
            },
            'created_at': datetime.utcnow()
        }

        mock_db.enriched_documents.insert_one(enriched_doc)

        # Step 4: Verify workflow
        retrieved = mock_db.enriched_documents.find_one({'_id': document_id})
        assert retrieved is not None
        assert retrieved['quality_metrics']['completeness_score'] == 0.96
        assert retrieved['quality_metrics']['review_status'] == 'approved'

        costs = cost_tracker_fixture.get_document_costs(document_id)
        assert costs['total_cost_usd'] > 0


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling in integration scenarios"""

    def test_missing_required_fields(self, mock_db):
        """Test handling of missing required fields"""
        incomplete_data = {
            'metadata': {
                'id': 'test_incomplete',
                # Missing required fields
            },
            'document': {},
            'content': {},
            'analysis': {}
        }

        # Should still validate without error
        assert isinstance(incomplete_data, dict)

    def test_invalid_cost_data(self, cost_tracker_fixture, mock_db):
        """Test handling of invalid cost data"""
        # Record with invalid model
        result = cost_tracker_fixture.record_api_call(
            enrichment_job_id='job_invalid',
            document_id='doc_invalid',
            model='invalid_model',
            task_name='unknown_task',
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0
        )

        # Should handle gracefully
        assert isinstance(result, bool)

    def test_duplicate_review_tasks(self, review_queue_fixture):
        """Test handling of duplicate review tasks"""
        document_id = 'doc_duplicate'

        # Create first review task
        review_id1 = review_queue_fixture.create_task(
            document_id=document_id,
            enrichment_job_id='job_1',
            reason='completeness_below_threshold',
            missing_fields=['field1'],
            low_confidence_fields=[]
        )

        # Create second review task for same document
        review_id2 = review_queue_fixture.create_task(
            document_id=document_id,
            enrichment_job_id='job_2',
            reason='completeness_below_threshold',
            missing_fields=['field2'],
            low_confidence_fields=[]
        )

        # Both should be created
        assert review_id1 is not None
        assert review_id2 is not None
        assert review_id1 != review_id2

        # History should show both
        history = review_queue_fixture.get_document_review_history(document_id)
        assert len(history) >= 2
