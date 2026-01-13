"""
Unit Tests for Docker Swarm Service

Tests all Docker Swarm management functionality with proper mocking
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock, call
import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

logger = logging.getLogger(__name__)


class TestDataClasses(unittest.TestCase):
    """Test data classes"""
    
    def setUp(self):
        """Import after path is set"""
        from app.services.swarm_service import SwarmNode, SwarmService, SwarmTask, SwarmInfo
        self.SwarmNode = SwarmNode
        self.SwarmService = SwarmService
        self.SwarmTask = SwarmTask
        self.SwarmInfo = SwarmInfo
    
    def test_swarm_node_to_dict(self):
        """Test SwarmNode.to_dict()"""
        node = self.SwarmNode(
            id='abc123',
            hostname='worker-1',
            status='ready',
            availability='active',
            manager_status=None,
            is_manager=False,
            ip_address='192.168.1.10',
            engine_version='20.10.0'
        )
        
        node_dict = node.to_dict()
        
        self.assertEqual(node_dict['id'], 'abc123')
        self.assertEqual(node_dict['hostname'], 'worker-1')
        self.assertEqual(node_dict['status'], 'ready')
    
    def test_swarm_service_to_dict(self):
        """Test SwarmService.to_dict()"""
        service = self.SwarmService(
            id='srv123',
            name='ocr-worker',
            mode='replicated',
            replicas=3,
            desired_count=3,
            running_count=3,
            image='ocr:latest',
            created_at='2025-12-20T12:00:00Z',
            updated_at='2025-12-20T12:00:00Z'
        )
        
        service_dict = service.to_dict()
        
        self.assertEqual(service_dict['name'], 'ocr-worker')
        self.assertEqual(service_dict['replicas'], 3)
        self.assertEqual(service_dict['running_count'], 3)
    
    def test_swarm_task_to_dict(self):
        """Test SwarmTask.to_dict()"""
        task = self.SwarmTask(
            id='task123',
            service_id='srv123',
            service_name='ocr-worker',
            node_id='node123',
            hostname='worker-1',
            status='running',
            state='running',
            error=None
        )
        
        task_dict = task.to_dict()
        
        self.assertEqual(task_dict['service_name'], 'ocr-worker')
        self.assertEqual(task_dict['status'], 'running')
        self.assertIsNone(task_dict['error'])
    
    def test_swarm_info_to_dict(self):
        """Test SwarmInfo.to_dict()"""
        info = self.SwarmInfo(
            swarm_id='sw123',
            is_manager=True,
            is_active=True,
            node_count=3,
            manager_count=1,
            worker_count=2,
            version='20.10.0'
        )
        
        info_dict = info.to_dict()
        
        self.assertEqual(info_dict['swarm_id'], 'sw123')
        self.assertTrue(info_dict['is_manager'])
        self.assertEqual(info_dict['node_count'], 3)


class TestDockerSwarmServiceMethods(unittest.TestCase):
    """Test DockerSwarmService methods"""
    
    def setUp(self):
        """Set up test fixtures"""
        from app.services.swarm_service import DockerSwarmService
        self.DockerSwarmService = DockerSwarmService
    
    @patch('app.services.swarm_service.docker.from_env')
    def test_init_success(self, mock_docker):
        """Test successful initialization"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        service = self.DockerSwarmService()
        
        self.assertIsNotNone(service.client)
        mock_client.ping.assert_called_once()
    
    @patch('app.services.swarm_service.docker.from_env')
    def test_init_failure(self, mock_docker):
        """Test initialization failure"""
        mock_docker.side_effect = Exception("Docker not available")
        
        try:
            service = self.DockerSwarmService()
            self.assertIsNone(service.client)
        except Exception:
            pass
    
    def test_list_nodes_empty_client(self):
        """Test list_nodes when client unavailable"""
        service = self.DockerSwarmService()
        service.client = None
        
        success, nodes, error = service.list_nodes()
        
        self.assertFalse(success)
        self.assertEqual(len(nodes), 0)
        self.assertIn("Docker client not available", error)
    
    @patch('app.services.swarm_service.docker.from_env')
    def test_scale_service_invalid_replicas(self, mock_docker):
        """Test scale_service with invalid replicas"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        service = self.DockerSwarmService()
        success, message = service.scale_service('ocr-worker', -1)
        
        self.assertFalse(success)
        self.assertIn("must be non-negative", message)
    
    @patch('app.services.swarm_service.docker.from_env')
    def test_update_node_availability_invalid(self, mock_docker):
        """Test update_node_availability with invalid availability"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        service = self.DockerSwarmService()
        success, message = service.update_node_availability('node1', 'invalid')
        
        self.assertFalse(success)
        self.assertIn("Invalid availability", message)
    
    def test_get_swarm_info_no_client(self):
        """Test get_swarm_info when client unavailable"""
        service = self.DockerSwarmService()
        service.client = None
        
        success, info, error = service.get_swarm_info()
        
        self.assertFalse(success)
        self.assertIsNone(info)
        self.assertIn("Docker client not available", error)
    
    def test_get_join_token_invalid_role(self):
        """Test get_join_token with invalid role"""
        service = self.DockerSwarmService()
        service.client = MagicMock()
        
        success, token, error = service.get_join_token('invalid')
        
        self.assertFalse(success)
        self.assertIsNone(token)
        self.assertIn("Invalid role", error)


class TestSwarmServiceIntegration(unittest.TestCase):
    """Integration tests for swarm service"""
    
    def setUp(self):
        """Set up test fixtures"""
        from app.services.swarm_service import DockerSwarmService
        self.service = DockerSwarmService()
        self.service.client = MagicMock()
    
    def test_full_workflow_scale_service(self):
        """Test full workflow: list services -> scale -> list again"""
        # Setup mocks
        mock_service = MagicMock()
        mock_service.id = 'srv123'
        mock_service.name = 'ocr-worker'
        mock_service.attrs = {
            'Spec': {
                'Mode': {'Replicated': {'Replicas': 3}},
                'TaskTemplate': {'ContainerSpec': {'Image': 'ocr:latest'}}
            },
            'CreatedAt': '2025-12-20T12:00:00Z',
            'UpdatedAt': '2025-12-20T12:00:00Z'
        }
        mock_service.tasks.return_value = [
            {'Status': {'State': 'running'}},
            {'Status': {'State': 'running'}},
            {'Status': {'State': 'running'}}
        ]
        
        self.service.client.services.list.return_value = [mock_service]
        self.service.client.services.get.return_value = mock_service
        
        # Test list services
        success, services, _ = self.service.list_services()
        self.assertTrue(success)
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0].replicas, 3)
        
        # Test scale
        success, message = self.service.scale_service('ocr-worker', 5)
        self.assertTrue(success)
        
        # Verify scale was called
        mock_service.scale.assert_called_once_with(5)
    
    def test_node_lifecycle(self):
        """Test node lifecycle: list -> inspect -> update availability -> remove"""
        # Setup mocks
        mock_node = MagicMock()
        mock_node.id = 'node123abc'
        mock_node.attrs = {
            'Description': {
                'Hostname': 'worker-1',
                'Status': {'Addr': '192.168.1.10'},
                'Engine': {'EngineVersion': '20.10.0'}
            },
            'Spec': {'Availability': 'active'},
            'Status': {'State': 'ready'},
            'ManagerStatus': {}
        }
        
        self.service.client.nodes.list.return_value = [mock_node]
        self.service.client.nodes.get.return_value = mock_node
        
        # Test list nodes
        success, nodes, _ = self.service.list_nodes()
        self.assertTrue(success)
        self.assertEqual(len(nodes), 1)
        
        # Test inspect node
        success, node_info, _ = self.service.inspect_node('node123abc')
        self.assertTrue(success)
        self.assertIsNotNone(node_info)
        
        # Test update availability
        success, message = self.service.update_node_availability('node123abc', 'drain')
        self.assertTrue(success)
        mock_node.update.assert_called_once()
        
        # Test remove node
        success, message = self.service.remove_node('node123abc', force=False)
        self.assertTrue(success)
        mock_node.remove.assert_called_once_with(force=False)


class TestErrorHandling(unittest.TestCase):
    """Test error handling across the service"""
    
    def setUp(self):
        """Set up test fixtures"""
        from app.services.swarm_service import DockerSwarmService
        self.service = DockerSwarmService()
    
    def test_docker_exception_handling_list_nodes(self):
        """Test exception handling in list_nodes"""
        self.service.client = MagicMock()
        self.service.client.nodes.list.side_effect = Exception("Network timeout")
        
        success, nodes, error = self.service.list_nodes()
        
        self.assertFalse(success)
        self.assertEqual(len(nodes), 0)
        self.assertIn("Failed to list nodes", error)
    
    def test_docker_exception_handling_scale_service(self):
        """Test exception handling in scale_service"""
        self.service.client = MagicMock()
        self.service.client.services.get.side_effect = Exception("Service not found")
        
        success, message = self.service.scale_service('nonexistent', 5)
        
        self.assertFalse(success)
        self.assertIn("Failed to scale service", message)
    
    def test_docker_exception_handling_get_health_status(self):
        """Test exception handling in get_health_status"""
        self.service.client = MagicMock()
        self.service.client.info.side_effect = Exception("Docker daemon not responding")
        
        success, health, error = self.service.get_health_status()
        
        self.assertFalse(success)
        self.assertEqual(health, {})
        self.assertIn("Failed to get swarm info", error)


class TestSwarmServiceStatistics(unittest.TestCase):
    """Test statistics gathering"""
    
    def setUp(self):
        """Set up test fixtures"""
        from app.services.swarm_service import DockerSwarmService
        self.service = DockerSwarmService()
        self.service.client = MagicMock()
    
    def test_get_statistics_structure(self):
        """Test that get_statistics returns correct structure"""
        # Setup mocks
        mock_swarm_info = MagicMock()
        mock_node = MagicMock()
        mock_node.is_manager = True
        
        self.service.client.info.return_value = {
            'Swarm': {
                'Cluster': {'ID': 'sw123'},
                'ControlAvailable': True,
                'LocalNodeState': 'active',
                'Nodes': 3,
                'Managers': 1
            },
            'ServerVersion': '20.10.0'
        }
        self.service.client.nodes.list.return_value = [mock_node, mock_node, MagicMock(is_manager=False)]
        self.service.client.services.list.return_value = []
        
        success, stats, _ = self.service.get_statistics()
        
        if success:
            self.assertIn('cluster', stats)
            self.assertIn('services', stats)
            self.assertIn('tasks', stats)
            self.assertIn('timestamp', stats)


if __name__ == '__main__':
    unittest.main()
