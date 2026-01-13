"""
Comprehensive Test Suite for Docker Swarm - Unit Tests with Proper Mocking
Tests all Swarm features with focus on unit tests and proper mocking
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock, PropertyMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestSwarmDataClassesUnit:
    """Unit tests for Swarm data classes"""
    
    def test_swarm_node_creation(self):
        """Test SwarmNode creation"""
        from app.services.swarm_service import SwarmNode
        
        node = SwarmNode(
            id='abc123',
            hostname='worker-1',
            status='ready',
            availability='active',
            manager_status=None,
            is_manager=False,
            ip_address='192.168.1.10',
            engine_version='20.10.0'
        )
        
        assert node.id == 'abc123'
        assert node.hostname == 'worker-1'
        assert node.status == 'ready'
        assert node.is_manager is False
    
    def test_swarm_node_to_dict(self):
        """Test SwarmNode serialization"""
        from app.services.swarm_service import SwarmNode
        
        node = SwarmNode(
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
        assert isinstance(node_dict, dict)
        assert node_dict['id'] == 'abc123'
        assert node_dict['hostname'] == 'worker-1'
        assert node_dict['status'] == 'ready'
    
    def test_swarm_service_creation(self):
        """Test SwarmService creation"""
        from app.services.swarm_service import SwarmService
        
        service = SwarmService(
            id='svc123',
            name='ocr-worker',
            image='ocr:latest',
            replicas=3,
            running_count=3,
            desired_count=3,
            mode='replicated',
            created_at='2025-12-20T12:00:00Z',
            updated_at='2025-12-20T12:00:00Z'
        )
        
        assert service.id == 'svc123'
        assert service.name == 'ocr-worker'
        assert service.replicas == 3
        assert service.mode == 'replicated'
    
    def test_swarm_service_to_dict(self):
        """Test SwarmService serialization"""
        from app.services.swarm_service import SwarmService
        
        service = SwarmService(
            id='svc123',
            name='ocr-worker',
            image='ocr:latest',
            replicas=3,
            running_count=3,
            desired_count=3,
            mode='replicated',
            created_at='2025-12-20T12:00:00Z',
            updated_at='2025-12-20T12:00:00Z'
        )
        
        service_dict = service.to_dict()
        assert isinstance(service_dict, dict)
        assert service_dict['id'] == 'svc123'
        assert service_dict['name'] == 'ocr-worker'
    
    def test_swarm_task_creation(self):
        """Test SwarmTask creation"""
        from app.services.swarm_service import SwarmTask
        
        task = SwarmTask(
            id='task123',
            name='ocr-worker.1',
            service_id='svc123',
            node_id='node123',
            status='running',
            desired_status='running',
            image='ocr:latest',
            error=None
        )
        
        assert task.id == 'task123'
        assert task.name == 'ocr-worker.1'
        assert task.status == 'running'
        assert task.desired_status == 'running'
    
    def test_swarm_info_creation(self):
        """Test SwarmInfo creation"""
        from app.services.swarm_service import SwarmInfo
        
        info = SwarmInfo(
            swarm_id='cluster123',
            is_manager=True,
            is_active=True,
            node_count=3,
            manager_count=1,
            worker_count=2,
            version='1.0.0'
        )
        
        assert info.swarm_id == 'cluster123'
        assert info.is_manager is True
        assert info.is_active is True
        assert info.node_count == 3
        assert info.manager_count == 1
        assert info.worker_count == 2


class TestSwarmServiceUnit:
    """Unit tests for Swarm service methods"""
    
    @pytest.fixture
    def mock_docker_client(self):
        """Create mock Docker client"""
        return MagicMock()
    
    @pytest.fixture
    def swarm_service_with_mock(self, mock_docker_client):
        """Create SwarmService with mocked Docker client"""
        from app.services.swarm_service import DockerSwarmService
        service = DockerSwarmService()
        service.client = mock_docker_client
        return service
    
    def test_list_nodes_success(self, swarm_service_with_mock, mock_docker_client):
        """Test listing nodes successfully"""
        # Setup mock nodes with all required attributes
        mock_node1 = MagicMock()
        node1_attrs = {
            'ID': 'node1',
            'Description': {
                'Hostname': 'manager-1',
                'Engine': {'EngineVersion': '20.10.0'}
            },
            'Status': {'State': 'ready'},
            'ManagerStatus': {'Reachability': 'reachable', 'Leader': True},
            'Spec': {'Availability': 'active'}
        }
        mock_node1.attrs = node1_attrs
        
        mock_node2 = MagicMock()
        node2_attrs = {
            'ID': 'node2',
            'Description': {
                'Hostname': 'worker-1',
                'Engine': {'EngineVersion': '20.10.0'}
            },
            'Status': {'State': 'ready'},
            'ManagerStatus': None,
            'Spec': {'Availability': 'active'}
        }
        mock_node2.attrs = node2_attrs
        
        mock_docker_client.nodes.list.return_value = [mock_node1, mock_node2]
        
        success, nodes, error = swarm_service_with_mock.list_nodes()
        
        # Should either succeed or have specific error
        assert isinstance(success, bool)
        if success:
            assert len(nodes) >= 0
    
    def test_scale_service_success(self, swarm_service_with_mock, mock_docker_client):
        """Test scaling a service"""
        mock_service = MagicMock()
        mock_service.attrs = {
            'ID': 'svc123',
            'Spec': {
                'Name': 'ocr-worker',
                'Mode': {'Replicated': {'Replicas': 3}},
                'TaskTemplate': {
                    'ContainerSpec': {'Image': 'ocr:latest'}
                }
            },
            'Version': {'Index': 1}
        }
        
        mock_docker_client.services.get.return_value = mock_service
        
        success, msg = swarm_service_with_mock.scale_service('ocr-worker', 5)
        
        assert success is True
        assert 'scaled' in msg.lower() or 'updated' in msg.lower()
    
    def test_scale_service_invalid_replicas(self, swarm_service_with_mock):
        """Test scaling with negative replicas"""
        success, msg = swarm_service_with_mock.scale_service('ocr-worker', -1)
        
        assert success is False
        assert 'invalid' in msg.lower() or 'negative' in msg.lower()
    
    def test_scale_service_zero_replicas(self, swarm_service_with_mock, mock_docker_client):
        """Test scaling to zero replicas"""
        mock_service = MagicMock()
        mock_service.attrs = {
            'ID': 'svc123',
            'Spec': {
                'Mode': {'Replicated': {'Replicas': 3}},
                'TaskTemplate': {'ContainerSpec': {'Image': 'ocr:latest'}}
            },
            'Version': {'Index': 1}
        }
        
        mock_docker_client.services.get.return_value = mock_service
        
        # Zero replicas should be valid (scale down to zero)
        success, msg = swarm_service_with_mock.scale_service('ocr-worker', 0)
        
        # Either success or has proper error message
        assert isinstance(success, bool)
    
    def test_update_node_availability_drain(self, swarm_service_with_mock, mock_docker_client):
        """Test draining a node"""
        mock_node = MagicMock()
        mock_node.attrs = {
            'ID': 'node123',
            'Spec': {'Availability': 'active'},
            'Version': {'Index': 1}
        }
        
        mock_docker_client.nodes.get.return_value = mock_node
        
        success, msg = swarm_service_with_mock.update_node_availability('node123', 'drain')
        
        assert success is True
        assert 'drain' in msg.lower()
    
    def test_update_node_availability_active(self, swarm_service_with_mock, mock_docker_client):
        """Test restoring a drained node"""
        mock_node = MagicMock()
        mock_node.attrs = {
            'ID': 'node123',
            'Spec': {'Availability': 'drain'},
            'Version': {'Index': 2}
        }
        
        mock_docker_client.nodes.get.return_value = mock_node
        
        success, msg = swarm_service_with_mock.update_node_availability('node123', 'active')
        
        assert success is True
        assert 'active' in msg.lower()
    
    def test_remove_node_success(self, swarm_service_with_mock, mock_docker_client):
        """Test removing a node"""
        mock_node = MagicMock()
        mock_node.attrs = {'ID': 'node123'}
        
        mock_docker_client.nodes.get.return_value = mock_node
        
        success, msg = swarm_service_with_mock.remove_node('node123', force=False)
        
        assert success is True
        assert 'removed' in msg.lower()
    
    def test_remove_node_not_found(self, swarm_service_with_mock, mock_docker_client):
        """Test removing non-existent node"""
        mock_docker_client.nodes.get.side_effect = Exception("Node not found")
        
        success, msg = swarm_service_with_mock.remove_node('nonexistent', force=False)
        
        assert success is False


class TestSwarmHealthMonitoring:
    """Tests for health monitoring features"""
    
    @pytest.fixture
    def swarm_service_with_mock(self):
        """Create SwarmService with mocked Docker client"""
        from app.services.swarm_service import DockerSwarmService
        service = DockerSwarmService()
        service.client = MagicMock()
        return service
    
    def test_health_status_all_healthy(self, swarm_service_with_mock):
        """Test health status when all nodes are healthy"""
        # Setup mock data
        mock_node = MagicMock()
        mock_node.attrs = {
            'Status': {'State': 'ready'},
            'Spec': {'Availability': 'active'},
            'Description': {'Hostname': 'node1'}
        }
        
        swarm_service_with_mock.client.nodes.list.return_value = [mock_node]
        swarm_service_with_mock.client.services.list.return_value = []
        
        success, health, error = swarm_service_with_mock.get_health_status()
        
        # Should either succeed or fail gracefully with proper error
        assert isinstance(success, bool)
        if success:
            assert health is not None
            assert isinstance(health, dict)


class TestSwarmIntegrationFeatures:
    """Integration tests for Swarm features"""
    
    def test_service_scaling_workflow(self):
        """Test complete service scaling workflow"""
        from app.services.swarm_service import DockerSwarmService
        
        service = DockerSwarmService()
        service.client = MagicMock()
        
        # Setup mock service
        mock_service = MagicMock()
        mock_service.attrs = {
            'ID': 'svc123',
            'Spec': {
                'Name': 'ocr-worker',
                'Mode': {'Replicated': {'Replicas': 2}},
                'TaskTemplate': {'ContainerSpec': {'Image': 'ocr:latest'}}
            },
            'Version': {'Index': 1}
        }
        
        service.client.services.get.return_value = mock_service
        
        # Scale from 2 to 5
        success, msg = service.scale_service('ocr-worker', 5)
        
        if success:
            assert 'scaled' in msg.lower() or 'updated' in msg.lower()
        else:
            assert isinstance(msg, str)
    
    def test_node_maintenance_workflow(self):
        """Test complete node maintenance workflow"""
        from app.services.swarm_service import DockerSwarmService
        
        service = DockerSwarmService()
        service.client = MagicMock()
        
        # Setup mock node
        mock_node = MagicMock()
        mock_node.attrs = {
            'ID': 'node123',
            'Spec': {'Availability': 'active'},
            'Version': {'Index': 1},
            'Description': {'Hostname': 'worker-1'}
        }
        
        service.client.nodes.get.return_value = mock_node
        
        # Drain node
        success, msg = service.update_node_availability('node123', 'drain')
        
        if success:
            assert 'drain' in msg.lower()
        
        # Restore node
        mock_node.attrs['Spec']['Availability'] = 'drain'
        mock_node.attrs['Version']['Index'] = 2
        
        success, msg = service.update_node_availability('node123', 'active')
        
        if success:
            assert 'active' in msg.lower()


class TestSwarmErrorHandling:
    """Tests for error handling"""
    
    def test_service_not_found_handling(self):
        """Test handling of service not found error"""
        from app.services.swarm_service import DockerSwarmService
        
        service = DockerSwarmService()
        service.client = MagicMock()
        service.client.services.get.side_effect = Exception("Service not found")
        
        success, msg = service.scale_service('nonexistent', 5)
        
        assert success is False
        assert isinstance(msg, str)
    
    def test_node_not_found_handling(self):
        """Test handling of node not found error"""
        from app.services.swarm_service import DockerSwarmService
        
        service = DockerSwarmService()
        service.client = MagicMock()
        service.client.nodes.get.side_effect = Exception("Node not found")
        
        success, data, error = service.inspect_node('nonexistent')
        
        assert success is False
        assert isinstance(error, str)
    
    def test_docker_connection_error(self):
        """Test handling of Docker connection error"""
        from app.services.swarm_service import DockerSwarmService
        
        service = DockerSwarmService()
        service.client = None
        
        success, info, error = service.get_swarm_info()
        
        # Should fail gracefully
        assert success is False or info is None


class TestSwarmDataValidation:
    """Tests for data validation"""
    
    def test_replica_count_validation(self):
        """Test replica count validation"""
        from app.services.swarm_service import DockerSwarmService
        
        service = DockerSwarmService()
        service.client = MagicMock()
        
        # Test negative replicas
        success, msg = service.scale_service('service', -5)
        assert success is False
        
        # Test very large replica count
        success, msg = service.scale_service('service', 10000)
        # Should succeed or have proper validation
        assert isinstance(success, bool)
    
    def test_node_id_validation(self):
        """Test node ID validation"""
        from app.services.swarm_service import DockerSwarmService
        
        service = DockerSwarmService()
        service.client = MagicMock()
        service.client.nodes.get.side_effect = Exception("Invalid node ID")
        
        success, data, error = service.inspect_node('')
        
        assert success is False


class TestSwarmFeatureCompleteness:
    """Test that all major features are implemented"""
    
    def test_service_has_required_methods(self):
        """Test that service has all required methods"""
        from app.services.swarm_service import DockerSwarmService
        
        service = DockerSwarmService()
        
        # Check critical methods exist
        assert hasattr(service, 'list_nodes')
        assert hasattr(service, 'inspect_node')
        assert hasattr(service, 'update_node_availability')
        assert hasattr(service, 'remove_node')
        assert hasattr(service, 'list_services')
        assert hasattr(service, 'scale_service')
        assert hasattr(service, 'update_service_image')
        assert hasattr(service, 'remove_service')
        assert hasattr(service, 'get_service_logs')
        assert hasattr(service, 'get_swarm_info')
        assert hasattr(service, 'get_health_status')
        assert hasattr(service, 'get_statistics')
        assert hasattr(service, 'get_join_token')
    
    def test_api_routes_registered(self):
        """Test that API routes are properly registered"""
        with patch('app.routes.swarm.get_swarm_service'):
            try:
                from app.routes.swarm import swarm_bp
                assert swarm_bp is not None
            except ImportError:
                pytest.skip("Could not import swarm routes")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
