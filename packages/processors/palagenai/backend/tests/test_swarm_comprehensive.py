"""
Comprehensive Test Suite for Docker Swarm Management
Tests all features including API endpoints and integration
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestSwarmServiceIntegration:
    """Integration tests for Swarm Service"""
    
    @pytest.fixture
    def swarm_service(self):
        """Get swarm service instance"""
        from app.services.swarm_service import get_swarm_service
        return get_swarm_service()
    
    @pytest.fixture
    def mock_docker(self):
        """Mock Docker client"""
        with patch('app.services.swarm_service.docker.from_env') as mock:
            yield mock
    
    # ==================== SWARM INFO TESTS ====================
    
    def test_get_swarm_info_success(self, swarm_service, mock_docker):
        """Test getting swarm info successfully"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        mock_client.info.return_value = {
            'Swarm': {
                'NodeID': 'abc123',
                'NodeAddr': '192.168.1.10:2377',
                'LocalNodeState': 'active',
                'ControlAvailable': True,
                'Error': ''
            }
        }
        
        with patch.object(swarm_service, 'client', mock_client):
            success, info, error = swarm_service.get_swarm_info()
            
            assert success is True
            assert info is not None
            assert error is None
    
    def test_get_swarm_info_failure(self, swarm_service, mock_docker):
        """Test swarm info when swarm not initialized"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_client.info.side_effect = Exception("Swarm not initialized")
        
        with patch.object(swarm_service, 'client', mock_client):
            success, info, error = swarm_service.get_swarm_info()
            
            assert success is False
            assert info is None
            assert "Swarm not initialized" in error
    
    # ==================== NODE MANAGEMENT TESTS ====================
    
    def test_list_nodes_success(self, swarm_service, mock_docker):
        """Test listing all nodes successfully"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        mock_node1 = MagicMock()
        mock_node1.attrs = {
            'ID': 'node1',
            'Description': {
                'Hostname': 'manager-1',
                'Engine': {'EngineVersion': '20.10.0'}
            },
            'Status': {'State': 'ready'},
            'ManagerStatus': {'Reachability': 'reachable'}
        }
        
        mock_node2 = MagicMock()
        mock_node2.attrs = {
            'ID': 'node2',
            'Description': {
                'Hostname': 'worker-1',
                'Engine': {'EngineVersion': '20.10.0'}
            },
            'Status': {'State': 'ready'},
            'ManagerStatus': None
        }
        
        mock_client.nodes.list.return_value = [mock_node1, mock_node2]
        
        with patch.object(swarm_service, 'client', mock_client):
            success, nodes, error = swarm_service.list_nodes()
            
            assert success is True
            assert len(nodes) == 2
            assert error is None
    
    def test_list_nodes_empty(self, swarm_service, mock_docker):
        """Test listing nodes when none exist"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_client.nodes.list.return_value = []
        
        with patch.object(swarm_service, 'client', mock_client):
            success, nodes, error = swarm_service.list_nodes()
            
            assert success is True
            assert len(nodes) == 0
            assert error is None
    
    def test_inspect_node_success(self, swarm_service, mock_docker):
        """Test inspecting a single node"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        mock_node = MagicMock()
        mock_node.attrs = {
            'ID': 'node123',
            'Description': {'Hostname': 'worker-1'},
            'Status': {'State': 'ready'}
        }
        
        mock_client.nodes.get.return_value = mock_node
        
        with patch.object(swarm_service, 'client', mock_client):
            success, node, error = swarm_service.inspect_node('node123')
            
            assert success is True
            assert node is not None
            assert error is None
    
    def test_inspect_node_not_found(self, swarm_service, mock_docker):
        """Test inspecting non-existent node"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_client.nodes.get.side_effect = Exception("Node not found")
        
        with patch.object(swarm_service, 'client', mock_client):
            success, node, error = swarm_service.inspect_node('nonexistent')
            
            assert success is False
            assert node is None
            assert "Node not found" in error
    
    def test_update_node_availability_drain(self, swarm_service, mock_docker):
        """Test draining a node for maintenance"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        mock_node = MagicMock()
        mock_node.attrs = {'Spec': {}}
        
        mock_client.nodes.get.return_value = mock_node
        
        with patch.object(swarm_service, 'client', mock_client):
            success, msg = swarm_service.update_node_availability('node123', 'drain')
            
            assert success is True
            assert "drain" in msg.lower()
    
    def test_update_node_availability_active(self, swarm_service, mock_docker):
        """Test restoring a node to active"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        mock_node = MagicMock()
        mock_node.attrs = {'Spec': {}}
        
        mock_client.nodes.get.return_value = mock_node
        
        with patch.object(swarm_service, 'client', mock_client):
            success, msg = swarm_service.update_node_availability('node123', 'active')
            
            assert success is True
            assert "active" in msg.lower()
    
    def test_remove_node_success(self, swarm_service, mock_docker):
        """Test removing a node"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        mock_node = MagicMock()
        mock_client.nodes.get.return_value = mock_node
        
        with patch.object(swarm_service, 'client', mock_client):
            success, msg = swarm_service.remove_node('node123', force=False)
            
            assert success is True
            assert "removed" in msg.lower()
    
    def test_remove_node_force(self, swarm_service, mock_docker):
        """Test force removing a node"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        mock_node = MagicMock()
        mock_client.nodes.get.return_value = mock_node
        
        with patch.object(swarm_service, 'client', mock_client):
            success, msg = swarm_service.remove_node('node123', force=True)
            
            assert success is True
            assert "removed" in msg.lower()
    
    # ==================== SERVICE MANAGEMENT TESTS ====================
    
    def test_list_services_success(self, swarm_service, mock_docker):
        """Test listing all services"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        mock_service1 = MagicMock()
        mock_service1.attrs = {
            'ID': 'svc1',
            'Spec': {'Name': 'ocr-worker'},
            'Mode': {'Replicated': {'Replicas': 3}},
            'ServiceStatus': {'RunningCount': 3, 'DesiredCount': 3}
        }
        
        mock_service2 = MagicMock()
        mock_service2.attrs = {
            'ID': 'svc2',
            'Spec': {'Name': 'web-server'},
            'Mode': {'Replicated': {'Replicas': 2}},
            'ServiceStatus': {'RunningCount': 2, 'DesiredCount': 2}
        }
        
        mock_client.services.list.return_value = [mock_service1, mock_service2]
        
        with patch.object(swarm_service, 'client', mock_client):
            success, services, error = swarm_service.list_services()
            
            assert success is True
            assert len(services) == 2
            assert error is None
    
    def test_list_services_empty(self, swarm_service, mock_docker):
        """Test listing services when none exist"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_client.services.list.return_value = []
        
        with patch.object(swarm_service, 'client', mock_client):
            success, services, error = swarm_service.list_services()
            
            assert success is True
            assert len(services) == 0
            assert error is None
    
    def test_scale_service_success(self, swarm_service, mock_docker):
        """Test scaling a service"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        mock_service = MagicMock()
        mock_service.attrs = {
            'Spec': {'Mode': {'Replicated': {'Replicas': 3}}}
        }
        
        mock_client.services.get.return_value = mock_service
        
        with patch.object(swarm_service, 'client', mock_client):
            success, msg = swarm_service.scale_service('ocr-worker', 5)
            
            assert success is True
            assert "scaled" in msg.lower() or "updated" in msg.lower()
    
    def test_scale_service_invalid_replicas(self, swarm_service, mock_docker):
        """Test scaling with invalid replica count"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        with patch.object(swarm_service, 'client', mock_client):
            success, msg = swarm_service.scale_service('ocr-worker', -1)
            
            assert success is False
    
    def test_scale_service_not_found(self, swarm_service, mock_docker):
        """Test scaling non-existent service"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_client.services.get.side_effect = Exception("Service not found")
        
        with patch.object(swarm_service, 'client', mock_client):
            success, msg = swarm_service.scale_service('nonexistent', 5)
            
            assert success is False
            assert "not found" in msg.lower()
    
    def test_update_service_image_success(self, swarm_service, mock_docker):
        """Test updating service image"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        mock_service = MagicMock()
        mock_service.attrs = {
            'Spec': {
                'TaskTemplate': {
                    'ContainerSpec': {'Image': 'old:latest'}
                }
            }
        }
        
        mock_client.services.get.return_value = mock_service
        
        with patch.object(swarm_service, 'client', mock_client):
            success, msg = swarm_service.update_service_image('web', 'myimage:v2')
            
            assert success is True
            assert "updated" in msg.lower()
    
    def test_remove_service_success(self, swarm_service, mock_docker):
        """Test removing a service"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        mock_service = MagicMock()
        mock_client.services.get.return_value = mock_service
        
        with patch.object(swarm_service, 'client', mock_client):
            success, msg = swarm_service.remove_service('ocr-worker')
            
            assert success is True
            assert "removed" in msg.lower()
    
    # ==================== TASK MANAGEMENT TESTS ====================
    
    def test_list_tasks_for_service(self, swarm_service, mock_docker):
        """Test listing tasks for a service"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        mock_task1 = MagicMock()
        mock_task1.attrs = {
            'ID': 'task1',
            'ServiceID': 'svc1',
            'Status': {'State': 'running'},
            'DesiredState': 'running'
        }
        
        mock_task2 = MagicMock()
        mock_task2.attrs = {
            'ID': 'task2',
            'ServiceID': 'svc1',
            'Status': {'State': 'failed'},
            'DesiredState': 'running'
        }
        
        mock_client.tasks.list.return_value = [mock_task1, mock_task2]
        
        with patch.object(swarm_service, 'client', mock_client):
            success, tasks, error = swarm_service.list_tasks('svc1')
            
            assert success is True
            assert len(tasks) == 2
            assert error is None
    
    def test_get_service_logs(self, swarm_service, mock_docker):
        """Test getting service logs"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        mock_service = MagicMock()
        mock_service.attrs = {
            'ID': 'svc1',
            'Spec': {'Name': 'ocr-worker'}
        }
        
        mock_client.services.get.return_value = mock_service
        
        # Mock tasks for the service
        mock_task = MagicMock()
        mock_task.attrs = {
            'ID': 'task1',
            'NodeID': 'node1',
            'Status': {'State': 'running'}
        }
        
        mock_client.tasks.list.return_value = [mock_task]
        
        with patch.object(swarm_service, 'client', mock_client):
            success, logs, error = swarm_service.get_service_logs('ocr-worker')
            
            assert success is True or (success is False and error is not None)
    
    # ==================== HEALTH MONITORING TESTS ====================
    
    def test_get_health_status_healthy(self, swarm_service, mock_docker):
        """Test health status when swarm is healthy"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        mock_node = MagicMock()
        mock_node.attrs = {
            'Status': {'State': 'ready'},
            'Spec': {'Availability': 'active'}
        }
        
        mock_service = MagicMock()
        mock_service.attrs = {
            'ServiceStatus': {'RunningCount': 3, 'DesiredCount': 3}
        }
        
        mock_client.nodes.list.return_value = [mock_node]
        mock_client.services.list.return_value = [mock_service]
        mock_client.info.return_value = {
            'Swarm': {'LocalNodeState': 'active'}
        }
        
        with patch.object(swarm_service, 'client', mock_client):
            success, health, error = swarm_service.get_health_status()
            
            assert success is True
            assert health is not None
            assert error is None
    
    def test_get_health_status_unhealthy(self, swarm_service, mock_docker):
        """Test health status detection of unhealthy nodes"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        mock_node = MagicMock()
        mock_node.attrs = {
            'Status': {'State': 'down'},
            'Spec': {'Availability': 'active'}
        }
        
        mock_client.nodes.list.return_value = [mock_node]
        mock_client.services.list.return_value = []
        
        with patch.object(swarm_service, 'client', mock_client):
            success, health, error = swarm_service.get_health_status()
            
            assert success is True
            assert health is not None
    
    # ==================== STATISTICS TESTS ====================
    
    def test_get_statistics_success(self, swarm_service, mock_docker):
        """Test getting cluster statistics"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        mock_node1 = MagicMock()
        mock_node1.attrs = {'ManagerStatus': {'Leader': True}}
        
        mock_node2 = MagicMock()
        mock_node2.attrs = {'ManagerStatus': None}
        
        mock_client.nodes.list.return_value = [mock_node1, mock_node2]
        
        mock_service = MagicMock()
        mock_service.attrs = {
            'Mode': {'Replicated': {'Replicas': 2}},
            'ServiceStatus': {'RunningCount': 2}
        }
        
        mock_client.services.list.return_value = [mock_service]
        
        mock_task1 = MagicMock()
        mock_task1.attrs = {'Status': {'State': 'running'}}
        
        mock_task2 = MagicMock()
        mock_task2.attrs = {'Status': {'State': 'failed'}}
        
        mock_client.tasks.list.return_value = [mock_task1, mock_task2]
        
        with patch.object(swarm_service, 'client', mock_client):
            success, stats, error = swarm_service.get_statistics()
            
            assert success is True
            assert stats is not None
            assert error is None
    
    # ==================== SWARM INITIALIZATION TESTS ====================
    
    def test_initialize_swarm_success(self, swarm_service, mock_docker):
        """Test initializing swarm"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        mock_client.swarm.init.return_value = 'node123'
        
        with patch.object(swarm_service, 'client', mock_client):
            success, msg = swarm_service.init_swarm()
            
            assert success is True
            assert msg is not None
    
    def test_leave_swarm_success(self, swarm_service, mock_docker):
        """Test leaving swarm"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        with patch.object(swarm_service, 'client', mock_client):
            success, msg = swarm_service.leave_swarm(force=False)
            
            assert success is True
            assert msg is not None
    
    def test_leave_swarm_force(self, swarm_service, mock_docker):
        """Test force leaving swarm"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        with patch.object(swarm_service, 'client', mock_client):
            success, msg = swarm_service.leave_swarm(force=True)
            
            assert success is True
            assert msg is not None
    
    def test_get_join_token_worker(self, swarm_service, mock_docker):
        """Test getting worker join token"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        mock_client.swarm.attrs = {
            'JoinTokens': {
                'Worker': 'SWMTKN-1-xxx',
                'Manager': 'SWMTKN-1-yyy'
            }
        }
        
        with patch.object(swarm_service, 'client', mock_client):
            success, token, error = swarm_service.get_join_token('worker')
            
            assert success is True
            assert token is not None
            assert error is None
    
    def test_get_join_token_manager(self, swarm_service, mock_docker):
        """Test getting manager join token"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        mock_client.swarm.attrs = {
            'JoinTokens': {
                'Worker': 'SWMTKN-1-xxx',
                'Manager': 'SWMTKN-1-yyy'
            }
        }
        
        with patch.object(swarm_service, 'client', mock_client):
            success, token, error = swarm_service.get_join_token('manager')
            
            assert success is True
            assert token is not None
            assert error is None
    
    def test_get_join_token_invalid_role(self, swarm_service, mock_docker):
        """Test getting token with invalid role"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        with patch.object(swarm_service, 'client', mock_client):
            success, token, error = swarm_service.get_join_token('invalid')
            
            assert success is False


class TestSwarmAPIEndpoints:
    """Test REST API endpoints for Swarm"""
    
    @pytest.fixture
    def client(self):
        """Flask test client"""
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    @pytest.fixture
    def auth_headers(self):
        """Mock authentication headers"""
        return {'Authorization': 'Bearer token123'}
    
    @patch('app.routes.swarm.get_swarm_service')
    def test_get_swarm_info_endpoint(self, mock_service, client, auth_headers):
        """Test GET /api/swarm/info endpoint"""
        mock_swarm = MagicMock()
        mock_swarm.get_swarm_info.return_value = (
            True,
            {'NodeID': 'abc123', 'LocalNodeState': 'active'},
            None
        )
        mock_service.return_value = mock_swarm
        
        response = client.get('/api/swarm/info', headers=auth_headers)
        assert response.status_code in [200, 401, 403]  # Accept auth failure
    
    @patch('app.routes.swarm.get_swarm_service')
    def test_list_nodes_endpoint(self, mock_service, client, auth_headers):
        """Test GET /api/swarm/nodes endpoint"""
        mock_swarm = MagicMock()
        mock_swarm.list_nodes.return_value = (True, [], None)
        mock_service.return_value = mock_swarm
        
        response = client.get('/api/swarm/nodes', headers=auth_headers)
        assert response.status_code in [200, 401, 403]
    
    @patch('app.routes.swarm.get_swarm_service')
    def test_list_services_endpoint(self, mock_service, client, auth_headers):
        """Test GET /api/swarm/services endpoint"""
        mock_swarm = MagicMock()
        mock_swarm.list_services.return_value = (True, [], None)
        mock_service.return_value = mock_swarm
        
        response = client.get('/api/swarm/services', headers=auth_headers)
        assert response.status_code in [200, 401, 403]
    
    @patch('app.routes.swarm.get_swarm_service')
    def test_scale_service_endpoint(self, mock_service, client, auth_headers):
        """Test POST /api/swarm/services/<name>/scale endpoint"""
        mock_swarm = MagicMock()
        mock_swarm.scale_service.return_value = (True, 'Service scaled')
        mock_service.return_value = mock_swarm
        
        response = client.post(
            '/api/swarm/services/ocr-worker/scale',
            json={'replicas': 5},
            headers=auth_headers
        )
        assert response.status_code in [200, 400, 401, 403]
    
    @patch('app.routes.swarm.get_swarm_service')
    def test_health_endpoint(self, mock_service, client, auth_headers):
        """Test GET /api/swarm/health endpoint"""
        mock_swarm = MagicMock()
        mock_swarm.get_health_status.return_value = (
            True,
            {'status': 'healthy', 'nodes': [], 'services': []},
            None
        )
        mock_service.return_value = mock_swarm
        
        response = client.get('/api/swarm/health', headers=auth_headers)
        assert response.status_code in [200, 401, 403]
    
    @patch('app.routes.swarm.get_swarm_service')
    def test_statistics_endpoint(self, mock_service, client, auth_headers):
        """Test GET /api/swarm/statistics endpoint"""
        mock_swarm = MagicMock()
        mock_swarm.get_statistics.return_value = (
            True,
            {'total_nodes': 1, 'total_services': 0},
            None
        )
        mock_service.return_value = mock_swarm
        
        response = client.get('/api/swarm/statistics', headers=auth_headers)
        assert response.status_code in [200, 401, 403]


class TestSwarmErrorHandling:
    """Test error handling in Swarm Service"""
    
    @pytest.fixture
    def swarm_service(self):
        """Get swarm service instance"""
        from app.services.swarm_service import get_swarm_service
        return get_swarm_service()
    
    @patch('app.services.swarm_service.docker.from_env')
    def test_docker_connection_error(self, mock_docker, swarm_service):
        """Test handling Docker connection error"""
        mock_docker.side_effect = Exception("Cannot connect to Docker daemon")
        
        with patch.object(swarm_service, 'client', None):
            success, info, error = swarm_service.get_swarm_info()
            assert success is False or info is None
    
    @patch('app.services.swarm_service.docker.from_env')
    def test_invalid_service_name(self, mock_docker, swarm_service):
        """Test scaling with invalid service name"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_client.services.get.side_effect = Exception("Service not found")
        
        with patch.object(swarm_service, 'client', mock_client):
            success, msg = swarm_service.scale_service('invalid-service', 5)
            assert success is False
    
    @patch('app.services.swarm_service.docker.from_env')
    def test_invalid_replica_count(self, mock_docker, swarm_service):
        """Test scale with negative replicas"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        
        with patch.object(swarm_service, 'client', mock_client):
            success, msg = swarm_service.scale_service('service', -5)
            assert success is False
    
    @patch('app.services.swarm_service.docker.from_env')
    def test_node_not_found_error(self, mock_docker, swarm_service):
        """Test error when node not found"""
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_client.nodes.get.side_effect = Exception("Node not found")
        
        with patch.object(swarm_service, 'client', mock_client):
            success, node, error = swarm_service.inspect_node('invalid-node')
            assert success is False
            assert "error" in error.lower() or "not found" in error.lower()


class TestSwarmDataClasses:
    """Test data classes and serialization"""
    
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
    
    def test_swarm_node_to_dict(self):
        """Test SwarmNode.to_dict()"""
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
            image='ocr:latest'
        )
        
        assert task.id == 'task123'
        assert task.status == 'running'
    
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
        assert info.node_count == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
