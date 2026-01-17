import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Add backend to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask, jsonify

class TestCancellation(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        
        # Mock dependencies before importing routes
        self.mongo_mock = MagicMock()
        self.bulk_job_mock = MagicMock()
        self.config_mock = MagicMock()
        self.nsq_coordinator_mock = MagicMock()
        
        # Patching imports in bulk.py
        self.patcher1 = patch('app.routes.bulk.mongo', self.mongo_mock)
        self.patcher2 = patch('app.models.bulk_job.BulkJob', self.bulk_job_mock)
        self.patcher3 = patch('app.routes.bulk.BulkJob', self.bulk_job_mock)
        self.patcher4 = patch('app.routes.bulk.Config', self.config_mock)
        self.patcher5 = patch('app.routes.bulk.NSQJobCoordinator', self.nsq_coordinator_mock)
        self.patcher6 = patch('app.utils.decorators.token_required', lambda f: f) # Disable auth for tests
        
        self.patcher1.start()
        self.patcher2.start()
        self.patcher3.start()
        self.patcher4.start()
        self.patcher5.start()
        self.patcher6.start()
        
        from app.routes.bulk import bulk_bp, processing_jobs, active_processors
        self.app.register_blueprint(bulk_bp)
        self.client = self.app.test_client()
        self.processing_jobs = processing_jobs
        self.active_processors = active_processors

    def tearDown(self):
        self.patcher1.stop()
        self.patcher2.stop()
        self.patcher3.stop()
        self.patcher4.stop()
        self.patcher5.stop()
        self.patcher6.stop()

    def test_stop_job_local(self):
        """Test stopping a job that is running locally (threading)"""
        job_id = "test_job_local"
        user_id = "user123"
        
        # Prepare mocks
        self.bulk_job_mock.find_by_job_id.return_value = {"job_id": job_id, "user_id": user_id}
        
        processor_mock = MagicMock()
        self.active_processors[job_id] = processor_mock
        self.processing_jobs[job_id] = {"status": "processing"}
        
        # Call endpoint
        response = self.client.post(f'/api/bulk/stop/{job_id}')
        
        # Verify results
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Job cancelled successfully')
        
        processor_mock.stop.assert_called_once()
        self.assertEqual(self.processing_jobs[job_id]['status'], 'cancelled')
        self.bulk_job_mock.update_status.assert_called_with(self.mongo_mock, job_id, 'cancelled')

    def test_stop_job_nsq(self):
        """Test stopping a job that is running via NSQ"""
        job_id = "test_job_nsq"
        user_id = "user123"
        
        # Prepare mocks
        self.bulk_job_mock.find_by_job_id.return_value = {"job_id": job_id, "user_id": user_id}
        self.config_mock.USE_NSQ = True
        
        # Ensure job is NOT in active_processors
        if job_id in self.active_processors:
            del self.active_processors[job_id]
        
        coordinator_instance = self.nsq_coordinator_mock.return_value
        
        # Call endpoint
        response = self.client.post(f'/api/bulk/stop/{job_id}')
        
        # Verify results
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Job cancellation request sent via NSQ')
        
        coordinator_instance.cancel_job.assert_called_with(job_id)
        self.bulk_job_mock.update_status.assert_called_with(self.mongo_mock, job_id, 'cancelled')

    def test_stop_job_not_found(self):
        """Test stopping a job that doesn't exist"""
        job_id = "nonexistent"
        self.bulk_job_mock.find_by_job_id.return_value = None
        
        response = self.client.post(f'/api/bulk/stop/{job_id}')
        self.assertEqual(response.status_code, 404)

if __name__ == '__main__':
    unittest.main()
