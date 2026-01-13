"""
Docker Swarm Service for OCR Worker Management

Provides comprehensive Docker Swarm management capabilities including:
- Swarm initialization and status
- Service management (deploy, remove, update)
- Worker scaling and monitoring
- Node management
- Health checks and diagnostics
"""

import docker
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import subprocess
from datetime import datetime

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    UNKNOWN = "unknown"


class NodeStatus(Enum):
    """Node status enumeration"""
    READY = "ready"
    DOWN = "down"
    UNKNOWN = "unknown"


class NodeAvailability(Enum):
    """Node availability enumeration"""
    ACTIVE = "active"
    PAUSE = "pause"
    DRAIN = "drain"


@dataclass
class SwarmNode:
    """Data class for swarm node information"""
    id: str
    hostname: str
    status: str
    availability: str
    manager_status: Optional[str]
    is_manager: bool
    ip_address: str
    engine_version: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SwarmService:
    """Data class for swarm service information"""
    id: str
    name: str
    mode: str
    replicas: int
    desired_count: int
    running_count: int
    image: str
    created_at: str
    updated_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SwarmTask:
    """Data class for swarm task information"""
    id: str
    service_id: str
    service_name: str
    node_id: str
    hostname: str
    status: str
    state: str
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SwarmInfo:
    """Data class for swarm cluster information"""
    swarm_id: str
    is_manager: bool
    is_active: bool
    node_count: int
    manager_count: int
    worker_count: int
    version: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DockerSwarmService:
    """
    Service for managing Docker Swarm operations
    
    Provides methods for:
    - Swarm management (init, leave, join)
    - Service deployment and management
    - Worker scaling
    - Node management
    - Monitoring and diagnostics
    """
    
    def __init__(self):
        """Initialize Docker client"""
        try:
            self.client = docker.from_env()
            self.client.ping()
            logger.info("Docker client initialized successfully")
        except docker.errors.DockerException as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.client = None
    
    def _check_client(self) -> bool:
        """Check if Docker client is available"""
        if self.client is None:
            logger.error("Docker client not available")
            return False
        return True
    
    # ==================== Swarm Information ====================
    
    def get_swarm_info(self) -> Tuple[bool, Optional[SwarmInfo], str]:
        """
        Get general swarm cluster information
        
        Returns:
            Tuple[bool, Optional[SwarmInfo], str]: (success, swarm_info, error_message)
        """
        try:
            if not self._check_client():
                return False, None, "Docker client not available"
            
            info = self.client.info()
            swarm = info.get('Swarm', {})
            
            if not swarm.get('Cluster'):
                return False, None, "Swarm not initialized"
            
            cluster = swarm.get('Cluster', {})
            
            swarm_info = SwarmInfo(
                swarm_id=cluster.get('ID', 'unknown'),
                is_manager=swarm.get('ControlAvailable', False),
                is_active=swarm.get('LocalNodeState') == 'active',
                node_count=info.get('Swarm', {}).get('Nodes', 0),
                manager_count=info.get('Swarm', {}).get('Managers', 0),
                worker_count=max(0, info.get('Swarm', {}).get('Nodes', 0) - info.get('Swarm', {}).get('Managers', 0)),
                version=info.get('ServerVersion', 'unknown')
            )
            
            return True, swarm_info, ""
        
        except Exception as e:
            error_msg = f"Failed to get swarm info: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def init_swarm(self, advertise_addr: str) -> Tuple[bool, str]:
        """
        Initialize Docker Swarm
        
        Args:
            advertise_addr: IP address to advertise for swarm
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            if not self._check_client():
                return False, "Docker client not available"
            
            # Check if already initialized
            info = self.client.info()
            swarm = info.get('Swarm', {})
            
            if swarm.get('Cluster'):
                return False, "Swarm already initialized"
            
            # Initialize swarm
            self.client.swarm.init(advertise_addr=advertise_addr)
            logger.info(f"Swarm initialized with advertise address: {advertise_addr}")
            return True, "Swarm initialized successfully"
        
        except Exception as e:
            error_msg = f"Failed to initialize swarm: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def leave_swarm(self, force: bool = False) -> Tuple[bool, str]:
        """
        Leave Docker Swarm
        
        Args:
            force: Force leave (even if manager)
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            if not self._check_client():
                return False, "Docker client not available"
            
            self.client.swarm.leave(force=force)
            logger.info("Left swarm successfully")
            return True, "Left swarm successfully"
        
        except Exception as e:
            error_msg = f"Failed to leave swarm: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_join_token(self, role: str = "worker") -> Tuple[bool, Optional[str], str]:
        """
        Get swarm join token for workers or managers
        
        Args:
            role: "worker" or "manager"
            
        Returns:
            Tuple[bool, Optional[str], str]: (success, token, error_message)
        """
        try:
            if not self._check_client():
                return False, None, "Docker client not available"
            
            if role == "worker":
                token = self.client.swarm.attrs['JoinTokens']['Worker']
            elif role == "manager":
                token = self.client.swarm.attrs['JoinTokens']['Manager']
            else:
                return False, None, f"Invalid role: {role}. Must be 'worker' or 'manager'"
            
            return True, token, ""
        
        except Exception as e:
            error_msg = f"Failed to get join token: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    # ==================== Node Management ====================
    
    def list_nodes(self) -> Tuple[bool, List[SwarmNode], str]:
        """
        List all swarm nodes
        
        Returns:
            Tuple[bool, List[SwarmNode], str]: (success, nodes, error_message)
        """
        try:
            if not self._check_client():
                return False, [], "Docker client not available"
            
            nodes = self.client.nodes.list()
            node_list = []
            
            for node in nodes:
                attrs = node.attrs
                spec = attrs.get('Spec', {})
                status = attrs.get('Status', {})
                manager_status = attrs.get('ManagerStatus', {})
                description = attrs.get('Description', {})
                
                node_obj = SwarmNode(
                    id=node.id[:12],
                    hostname=attrs.get('Description', {}).get('Hostname', 'unknown'),
                    status=status.get('State', 'unknown'),
                    availability=spec.get('Availability', 'unknown'),
                    manager_status='leader' if manager_status.get('Leader') else 'reachable' if manager_status else None,
                    is_manager=bool(manager_status),
                    ip_address=description.get('Status', {}).get('Addr', 'unknown'),
                    engine_version=description.get('Engine', {}).get('EngineVersion', 'unknown')
                )
                node_list.append(node_obj)
            
            return True, node_list, ""
        
        except Exception as e:
            error_msg = f"Failed to list nodes: {str(e)}"
            logger.error(error_msg)
            return False, [], error_msg
    
    def inspect_node(self, node_id: str) -> Tuple[bool, Optional[Dict], str]:
        """
        Get detailed information about a node
        
        Args:
            node_id: Node ID
            
        Returns:
            Tuple[bool, Optional[Dict], str]: (success, node_info, error_message)
        """
        try:
            if not self._check_client():
                return False, None, "Docker client not available"
            
            node = self.client.nodes.get(node_id)
            return True, node.attrs, ""
        
        except Exception as e:
            error_msg = f"Failed to inspect node: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def update_node_availability(self, node_id: str, availability: str) -> Tuple[bool, str]:
        """
        Update node availability (active, pause, or drain)
        
        Args:
            node_id: Node ID
            availability: 'active', 'pause', or 'drain'
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            if not self._check_client():
                return False, "Docker client not available"
            
            if availability not in ['active', 'pause', 'drain']:
                return False, f"Invalid availability: {availability}"
            
            node = self.client.nodes.get(node_id)
            node.update({'Spec': {'Availability': availability}})
            
            logger.info(f"Updated node {node_id[:12]} availability to {availability}")
            return True, f"Node availability updated to {availability}"
        
        except Exception as e:
            error_msg = f"Failed to update node availability: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def remove_node(self, node_id: str, force: bool = False) -> Tuple[bool, str]:
        """
        Remove a node from swarm
        
        Args:
            node_id: Node ID
            force: Force removal
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            if not self._check_client():
                return False, "Docker client not available"
            
            node = self.client.nodes.get(node_id)
            node.remove(force=force)
            
            logger.info(f"Removed node {node_id[:12]}")
            return True, "Node removed successfully"
        
        except Exception as e:
            error_msg = f"Failed to remove node: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    # ==================== Service Management ====================
    
    def deploy_stack(self, stack_file: str, stack_name: str) -> Tuple[bool, str]:
        """
        Deploy a stack from compose file
        
        Args:
            stack_file: Path to docker-compose or stack file
            stack_name: Name for the stack
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            if not self._check_client():
                return False, "Docker client not available"
            
            cmd = f"docker stack deploy -c {stack_file} {stack_name}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                error_msg = f"Failed to deploy stack: {result.stderr}"
                logger.error(error_msg)
                return False, error_msg
            
            logger.info(f"Stack {stack_name} deployed successfully")
            return True, f"Stack {stack_name} deployed successfully"
        
        except Exception as e:
            error_msg = f"Failed to deploy stack: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def list_services(self, filters: Optional[Dict] = None) -> Tuple[bool, List[SwarmService], str]:
        """
        List all swarm services
        
        Args:
            filters: Optional filters for services
            
        Returns:
            Tuple[bool, List[SwarmService], str]: (success, services, error_message)
        """
        try:
            logger.info(f"[SWARM] Listing services with filters: {filters}")
            
            if not self._check_client():
                logger.error("[SWARM] Docker client not available")
                return False, [], "Docker client not available"
            
            services = self.client.services.list(filters=filters)
            logger.info(f"[SWARM] Found {len(services)} services")
            
            service_list = []
            
            for service in services:
                logger.info(f"[SWARM] Processing service: {service.name}")
                attrs = service.attrs
                spec = attrs.get('Spec', {})
                mode = spec.get('Mode', {})
                
                # Get service stats
                api_client = self.client.api
                tasks = api_client.tasks(filters={'service': service.id})
                logger.info(f"[SWARM] Service {service.name} has {len(tasks)} tasks")
                
                running = sum(1 for t in tasks if t.get('Status', {}).get('State') == 'running')
                desired = len(tasks)
                
                logger.info(f"[SWARM] Service {service.name}: {running}/{desired} running")
                
                if 'Replicated' in mode:
                    replica_count = mode['Replicated'].get('Replicas', 0)
                else:
                    replica_count = desired
                
                service_obj = SwarmService(
                    id=service.id[:12],
                    name=service.name,
                    mode=list(mode.keys())[0] if mode else 'unknown',
                    replicas=replica_count,
                    desired_count=desired,
                    running_count=running,
                    image=spec.get('TaskTemplate', {}).get('ContainerSpec', {}).get('Image', 'unknown'),
                    created_at=attrs.get('CreatedAt', 'unknown'),
                    updated_at=attrs.get('UpdatedAt', 'unknown')
                )
                logger.info(f"[SWARM] Created service object: {service_obj.to_dict()}")
                service_list.append(service_obj)
            
            logger.info(f"[SWARM] Returning {len(service_list)} services")
            return True, service_list, ""
        
        except Exception as e:
            error_msg = f"Failed to list services: {str(e)}"
            logger.error(f"[SWARM] {error_msg}", exc_info=True)
            return False, [], error_msg
    
    def scale_service(self, service_name: str, replicas: int) -> Tuple[bool, str]:
        """
        Scale a service to desired number of replicas
        
        Args:
            service_name: Name of the service
            replicas: Number of replicas
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            if not self._check_client():
                return False, "Docker client not available"
            
            if replicas < 0:
                return False, "Number of replicas must be non-negative"
            
            service = self.client.services.get(service_name)
            service.scale(replicas)
            
            logger.info(f"Scaled service {service_name} to {replicas} replicas")
            return True, f"Service scaled to {replicas} replicas"
        
        except Exception as e:
            error_msg = f"Failed to scale service: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def update_service_image(self, service_name: str, image: str) -> Tuple[bool, str]:
        """
        Update service image
        
        Args:
            service_name: Name of the service
            image: New image name
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            if not self._check_client():
                return False, "Docker client not available"
            
            service = self.client.services.get(service_name)
            service_attrs = service.attrs
            
            # Update the image in the service spec using low-level API
            api_client = self.client.api
            spec = service_attrs['Spec'].copy()
            spec['TaskTemplate']['ContainerSpec']['Image'] = image
            
            api_client.service_update(
                service.id,
                service_attrs['Version']['Index'],
                spec
            )
            
            logger.info(f"Updated service {service_name} image to {image}")
            return True, f"Service image updated to {image}"
        
        except Exception as e:
            error_msg = f"Failed to update service image: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def remove_service(self, service_name: str) -> Tuple[bool, str]:
        """
        Remove a service from swarm
        
        Args:
            service_name: Name of the service
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            if not self._check_client():
                return False, "Docker client not available"
            
            service = self.client.services.get(service_name)
            service.remove()
            
            logger.info(f"Removed service {service_name}")
            return True, f"Service {service_name} removed successfully"
        
        except Exception as e:
            error_msg = f"Failed to remove service: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    # ==================== Task Management ====================
    
    def list_service_tasks(self, service_name: str) -> Tuple[bool, List[SwarmTask], str]:
        """
        List all tasks for a service
        
        Args:
            service_name: Name of the service
            
        Returns:
            Tuple[bool, List[SwarmTask], str]: (success, tasks, error_message)
        """
        try:
            if not self._check_client():
                return False, [], "Docker client not available"
            
            service = self.client.services.get(service_name)
            api_client = self.client.api
            tasks = api_client.tasks(filters={'service': service.id})
            task_list = []
            
            for task in tasks:
                status = task.get('Status', {})
                task_obj = SwarmTask(
                    id=task.get('ID', 'unknown')[:12],
                    service_id=task.get('ServiceID', 'unknown')[:12],
                    service_name=service_name,
                    node_id=task.get('NodeID', 'unknown')[:12],
                    hostname=task.get('NodeID', 'unknown'),
                    status=status.get('State', 'unknown'),
                    state=task.get('DesiredState', 'unknown'),
                    error=status.get('Err', None)
                )
                task_list.append(task_obj)
            
            return True, task_list, ""
        
        except Exception as e:
            error_msg = f"Failed to list service tasks: {str(e)}"
            logger.error(error_msg)
            return False, [], error_msg
    
    def get_service_logs(self, service_name: str, tail: int = 100) -> Tuple[bool, List[str], str]:
        """
        Get logs from service tasks
        
        Args:
            service_name: Name of the service
            tail: Number of log lines to return
            
        Returns:
            Tuple[bool, List[str], str]: (success, logs, error_message)
        """
        try:
            if not self._check_client():
                return False, [], "Docker client not available"
            
            # Use docker service logs command
            cmd = f"docker service logs --tail {tail} {service_name} 2>&1"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            logs = result.stdout.split('\n') if result.stdout else []
            
            return True, logs, ""
        
        except Exception as e:
            error_msg = f"Failed to get service logs: {str(e)}"
            logger.error(error_msg)
            return False, [], error_msg
    
    # ==================== Health & Diagnostics ====================
    
    def get_health_status(self) -> Tuple[bool, Dict[str, Any], str]:
        """
        Get comprehensive health status of swarm and services
        
        Returns:
            Tuple[bool, Dict[str, Any], str]: (success, health_status, error_message)
        """
        try:
            if not self._check_client():
                return False, {}, "Docker client not available"
            
            # Get swarm info
            success, swarm_info, error = self.get_swarm_info()
            if not success:
                return False, {}, error
            
            # Get nodes
            success, nodes, error = self.list_nodes()
            if not success:
                nodes = []
            
            # Get services
            success, services, error = self.list_services()
            if not success:
                services = []
            
            # Calculate health metrics
            healthy_nodes = sum(1 for n in nodes if n.status == 'ready')
            healthy_services = sum(1 for s in services if s.running_count == s.desired_count)
            
            health_status = {
                'swarm': swarm_info.to_dict() if swarm_info else {},
                'nodes': {
                    'total': len(nodes),
                    'ready': healthy_nodes,
                    'unhealthy': len(nodes) - healthy_nodes,
                    'list': [n.to_dict() for n in nodes]
                },
                'services': {
                    'total': len(services),
                    'healthy': healthy_services,
                    'unhealthy': len(services) - healthy_services,
                    'list': [s.to_dict() for s in services]
                },
                'overall_health': 'healthy' if healthy_nodes == len(nodes) and healthy_services == len(services) else 'degraded'
            }
            
            return True, health_status, ""
        
        except Exception as e:
            error_msg = f"Failed to get health status: {str(e)}"
            logger.error(error_msg)
            return False, {}, error_msg
    
    def get_statistics(self) -> Tuple[bool, Dict[str, Any], str]:
        """
        Get comprehensive statistics about swarm
        
        Returns:
            Tuple[bool, Dict[str, Any], str]: (success, statistics, error_message)
        """
        try:
            if not self._check_client():
                return False, {}, "Docker client not available"
            
            # Get swarm info
            success, swarm_info, _ = self.get_swarm_info()
            
            # Get nodes
            success, nodes, _ = self.list_nodes()
            
            # Get services
            success, services, _ = self.list_services()
            
            # Get tasks for all services
            total_tasks = 0
            running_tasks = 0
            failed_tasks = 0
            
            for service in services:
                success, tasks, _ = self.list_service_tasks(service.name)
                if success:
                    total_tasks += len(tasks)
                    running_tasks += sum(1 for t in tasks if t.status == 'running')
                    failed_tasks += sum(1 for t in tasks if t.status in ['failed', 'rejected'])
            
            statistics = {
                'cluster': {
                    'node_count': len(nodes),
                    'manager_count': sum(1 for n in nodes if n.is_manager),
                    'worker_count': sum(1 for n in nodes if not n.is_manager),
                },
                'services': {
                    'total': len(services),
                    'total_replicas': sum(s.replicas for s in services),
                    'running_replicas': sum(s.running_count for s in services),
                },
                'tasks': {
                    'total': total_tasks,
                    'running': running_tasks,
                    'failed': failed_tasks,
                    'pending': total_tasks - running_tasks - failed_tasks,
                },
                'timestamp': datetime.now().isoformat()
            }
            
            return True, statistics, ""
        
        except Exception as e:
            error_msg = f"Failed to get statistics: {str(e)}"
            logger.error(error_msg)
            return False, {}, error_msg
    def promote_node(self, node_id: str) -> Tuple[bool, str]:
        """Promote a worker node to manager"""
        try:
            node = self.client.nodes.get(node_id)
            node.update({'Spec': {'Role': 'manager'}})
            logger.info(f"Promoted node {node_id} to manager")
            return True, f"Node {node_id} promoted to manager"
        except Exception as e:
            error_msg = f"Failed to promote node: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def demote_node(self, node_id: str) -> Tuple[bool, str]:
        """Demote a manager node to worker"""
        try:
            node = self.client.nodes.get(node_id)
            node.update({'Spec': {'Role': 'worker'}})
            logger.info(f"Demoted node {node_id} to worker")
            return True, f"Node {node_id} demoted to worker"
        except Exception as e:
            error_msg = f"Failed to demote node: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def create_service(self, name: str, image: str, replicas: int = 1,
                      mongo_uri: str = None, env_vars: dict = None) -> Tuple[bool, str]:
        """Create a new swarm service with full worker configuration"""
        try:
            logger.info(f"[SWARM] Creating service - name: {name}, image: {image}, replicas: {replicas}")

            # Validate service name - minimum 3 characters
            name = name.strip()
            logger.info(f"[SWARM] Validating service name: {name}")

            if not name or len(name) < 3:
                logger.warning(f"[SWARM] Invalid service name length: {len(name)}")
                return False, "Service name must be at least 3 characters long"

            if not name.replace('-', '').replace('_', '').isalnum():
                logger.warning(f"[SWARM] Service name contains invalid characters: {name}")
                return False, "Service name can only contain alphanumeric characters, hyphens, and underscores"

            # Clean up image name - remove scheme and domain
            clean_image = image.strip()
            logger.info(f"[SWARM] Original image: {clean_image}")

            # Remove http/https scheme
            if clean_image.startswith('https://'):
                clean_image = clean_image[8:]
                logger.info(f"[SWARM] Removed https:// prefix: {clean_image}")
            elif clean_image.startswith('http://'):
                clean_image = clean_image[7:]
                logger.info(f"[SWARM] Removed http:// prefix: {clean_image}")

            # Extract image name after the registry (after first /)
            # e.g., "registry.docgenai.com:5010/gvpocr-worker-updated:latest" -> "gvpocr-worker-updated:latest"
            if '/' in clean_image:
                parts = clean_image.split('/', 1)
                if len(parts) > 1:
                    clean_image = parts[1]
                    logger.info(f"[SWARM] Extracted image name after registry: {clean_image}")

            # Validate image format
            if not clean_image or ' ' in clean_image:
                logger.error(f"[SWARM] Invalid image name after cleaning: {clean_image}")
                return False, f"Invalid image name: {image}"

            # Get environment config from .env or use defaults
            import os
            mongo_username = os.getenv('MONGO_ROOT_USERNAME', 'gvpocr_admin')
            mongo_password = os.getenv('MONGO_ROOT_PASSWORD', 'gvp@123')

            # Use provided mongo_uri or construct default
            if not mongo_uri:
                mongo_uri = f"mongodb://{mongo_username}:{mongo_password}@mongodb:27017/gvpocr?authSource=admin"

            # Base environment variables for worker
            environment = {
                # MongoDB Configuration
                'MONGO_URI': mongo_uri,

                # NSQ Configuration
                'USE_NSQ': 'true',
                'NSQD_ADDRESS': 'nsqd:4150',
                'NSQLOOKUPD_ADDRESSES': 'nsqlookupd:4161',

                # Backend API Server
                'GVPOCR_SERVER_URL': 'http://backend:5000',

                # OCR Provider Configuration
                'GOOGLE_APPLICATION_CREDENTIALS': '/app/google-credentials.json',
                'DEFAULT_OCR_PROVIDER': os.getenv('DEFAULT_OCR_PROVIDER', 'google_vision'),
                'GVPOCR_PATH': '/app/Bhushanji',
                'NEWSLETTERS_PATH': '/app/newsletters',

                # Provider Enablement
                'GOOGLE_VISION_ENABLED': os.getenv('GOOGLE_VISION_ENABLED', 'true'),
                'TESSERACT_ENABLED': os.getenv('TESSERACT_ENABLED', 'true'),
                'OLLAMA_ENABLED': os.getenv('OLLAMA_ENABLED', 'false'),
                'LLAMACPP_ENABLED': os.getenv('LLAMACPP_ENABLED', 'false'),
                'VLLM_ENABLED': 'false',
                'EASYOCR_ENABLED': 'false',
                'AZURE_ENABLED': 'false',

                # Tesseract Configuration
                'TESSERACT_CMD': '/usr/bin/tesseract',
            }

            # Merge custom environment variables
            if env_vars:
                environment.update(env_vars)

            # Convert environment dict to list of "KEY=VALUE" strings
            env_list = [f"{k}={v}" for k, v in environment.items()]

            # Worker command - run as NSQ worker
            command = [
                'python', 'run_worker.py',
                '--worker-id', '{{.Service.Name}}-{{.Task.Slot}}',
                '--nsqlookupd', 'nsqlookupd:4161'
            ]

            # Mounts for credentials and shared folders
            mounts = [
                # Google credentials (read-only)
                docker.types.Mount(
                    target='/app/google-credentials.json',
                    source='gvpocr_google-credentials',
                    type='volume',
                    read_only=True
                ),
                # Shared Bhushanji folder (read-only)
                docker.types.Mount(
                    target='/app/Bhushanji',
                    source='bhushanji_shared',
                    type='volume',
                    read_only=True
                ),
            ]

            # Network configuration - attach to gvpocr network
            networks = ['gvpocr_gvpocr-network']

            logger.info(f"[SWARM] Final cleaned image: {clean_image}")
            logger.info(f"[SWARM] Command: {' '.join(command)}")
            logger.info(f"[SWARM] Networks: {networks}")
            logger.info(f"[SWARM] Environment variables: {len(env_list)} vars")
            logger.info(f"[SWARM] Creating Docker service with name={name}, image={clean_image}, mode=replicated")

            # Use low-level API for proper service creation
            api_client = self.client.api

            # Build service specification
            service_spec = {
                'name': name,
                'labels': {'created_by': 'gvpocr', 'worker_type': 'ocr_worker'},
                'task_template': {
                    'ContainerSpec': {
                        'Image': clean_image,
                        'Command': command,
                        'Env': env_list,
                        'Mounts': [
                            {
                                'Type': 'volume',
                                'Source': 'gvpocr_google-credentials',
                                'Target': '/app/google-credentials.json',
                                'ReadOnly': True
                            },
                            {
                                'Type': 'volume',
                                'Source': 'gvpocr_bhushanji_shared',
                                'Target': '/app/Bhushanji',
                                'ReadOnly': True
                            }
                        ]
                    },
                    'Networks': [{'Target': 'gvpocr_gvpocr-network'}]
                },
                'mode': {
                    'Replicated': {
                        'Replicas': replicas
                    }
                }
            }

            logger.info(f"[SWARM] Service spec: {service_spec}")

            # Create service using low-level API
            service_id = api_client.create_service(**service_spec)
            service = self.client.services.get(service_id['ID'])

            logger.info(f"[SWARM] Service created with ID: {service.id}, name: {service.name}")
            logger.info(f"[SWARM] Successfully created service {name} with {replicas} replicas")
            return True, f"Service {name} created successfully with {replicas} replicas"

        except Exception as e:
            error_msg = f"Failed to create service: {str(e)}"
            logger.error(f"[SWARM] {error_msg}", exc_info=True)
            return False, error_msg

    def list_all_tasks(self) -> Tuple[bool, List[SwarmTask], str]:
        """List all tasks in the swarm"""
        try:
            if not self._check_client():
                return False, [], "Docker client not available"
            
            tasks = []
            
            # Use low-level API for tasks (Docker SDK v2.0 compatibility)
            api_client = self.client.api
            task_objects = api_client.tasks()
            services_map = {s.id: s.attrs['Spec']['Name'] for s in self.client.services.list()}
            nodes_map = {n.id: n.attrs['Description']['Hostname'] for n in self.client.nodes.list()}
            
            for task in task_objects:
                service_id = task.get('ServiceID', '')
                node_id = task.get('NodeID', '')
                
                tasks.append(SwarmTask(
                    id=task['ID'][:12],
                    service_id=service_id[:12] if service_id else 'unknown',
                    service_name=services_map.get(service_id, 'unknown'),
                    node_id=node_id[:12] if node_id else 'unknown',
                    hostname=nodes_map.get(node_id, 'unknown'),
                    status=task.get('Status', {}).get('State', 'unknown'),
                    state=task.get('DesiredState', 'unknown'),
                    error=task.get('Status', {}).get('Err', None),
                ))
            
            logger.info(f"Retrieved {len(tasks)} tasks from swarm")
            return True, tasks, ""
        
        except Exception as e:
            error_msg = f"Failed to list tasks: {str(e)}"
            logger.error(error_msg)
            return False, [], error_msg

    def join_node_to_swarm(self, host: str, username: str, 
                          ssh_key: Optional[str] = None,
                          ssh_key_path: Optional[str] = None) -> Tuple[bool, str, str]:
        """
        Join a remote machine to the Swarm cluster
        
        Args:
            host: Remote host IP or hostname
            username: SSH username
            ssh_key: SSH private key content (optional)
            ssh_key_path: Path to SSH private key file (optional)
            
        Returns:
            Tuple of (success, message, error_message)
        """
        try:
            import paramiko
            import tempfile
            
            logger.info(f"[SWARM] Attempting to join node: {username}@{host}")
            
            # Get worker join token
            logger.info("[SWARM] Getting worker join token from manager...")
            try:
                result = subprocess.run(['docker', 'swarm', 'join-token', 'worker', '-q'],
                                      capture_output=True, text=True, timeout=10)
                if result.returncode != 0:
                    error_msg = f"Failed to get join token: {result.stderr}"
                    logger.error(f"[SWARM] {error_msg}")
                    return False, "", error_msg
                
                join_token = result.stdout.strip()
                logger.info(f"[SWARM] Got join token: {join_token[:20]}...")
            except Exception as e:
                error_msg = f"Failed to retrieve join token: {str(e)}"
                logger.error(f"[SWARM] {error_msg}")
                return False, "", error_msg
            
            # Get manager IP address
            try:
                result = subprocess.run(['docker', 'node', 'inspect', 'self', '--format', '{{.Status.Addr}}'],
                                      capture_output=True, text=True, timeout=10)
                manager_addr = result.stdout.strip() if result.returncode == 0 else host
                logger.info(f"[SWARM] Manager address: {manager_addr}")
            except:
                manager_addr = host
            
            # Connect via SSH and join swarm
            logger.info(f"[SWARM] Connecting to {username}@{host}...")
            
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Load SSH key if provided
            if ssh_key_path:
                logger.info(f"[SWARM] Using SSH key from: {ssh_key_path}")
                ssh.connect(host, username=username, key_filename=ssh_key_path, timeout=30)
            elif ssh_key:
                logger.info("[SWARM] Using provided SSH key")
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as f:
                    f.write(ssh_key)
                    key_file = f.name
                try:
                    ssh.connect(host, username=username, key_filename=key_file, timeout=30)
                finally:
                    import os
                    os.unlink(key_file)
            else:
                logger.error("[SWARM] No SSH key provided")
                return False, "", "SSH key or key path is required"
            
            logger.info(f"[SWARM] Connected to {host}")
            
            # Execute join command on remote machine
            join_command = f"docker swarm join --token {join_token} {manager_addr}:2377"
            logger.info(f"[SWARM] Executing join command: {join_command}")
            
            stdin, stdout, stderr = ssh.exec_command(join_command, timeout=60)
            exit_code = stdout.channel.recv_exit_status()
            out_msg = stdout.read().decode('utf-8')
            err_msg = stderr.read().decode('utf-8')
            
            ssh.close()
            
            if exit_code != 0 and "context deadline exceeded" not in err_msg:
                # context deadline exceeded is expected and ok - join happens in background
                error_msg = f"Join command failed: {err_msg}"
                logger.error(f"[SWARM] {error_msg}")
                return False, "", error_msg
            
            logger.info(f"[SWARM] Node join initiated successfully")
            
            # Wait a moment for the join to be processed
            import time
            time.sleep(5)
            
            # Verify node joined
            logger.info(f"[SWARM] Verifying node {host} joined the cluster...")
            try:
                result = subprocess.run(['docker', 'node', 'ls', '--filter', f'name={host}', '--format', 'json'],
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout.strip():
                    logger.info(f"[SWARM] Node {host} successfully joined the cluster")
                    return True, f"Node {host} successfully joined the Swarm cluster", ""
                else:
                    # Node might still be joining, give it more time
                    logger.warning(f"[SWARM] Node not yet visible in cluster, might be joining...")
                    return True, f"Node {host} join command sent. Node will appear in cluster soon", ""
            except Exception as e:
                logger.warning(f"[SWARM] Could not verify node join: {str(e)}")
                return True, f"Node {host} join initiated. Please verify manually", ""
        
        except Exception as e:
            error_msg = f"Failed to join node to swarm: {str(e)}"
            logger.error(f"[SWARM] {error_msg}")
            import traceback
            logger.error(traceback.format_exc())
            return False, "", error_msg

    def launch_remote_worker(self, host: str, username: str, password: str, 
                            docker_image: str, worker_name: str, 
                            replica_count: int = 1) -> Tuple[bool, Dict[str, Any], str]:
        """
        Launch Docker worker on a remote machine via SSH
        
        Args:
            host: Remote host IP or hostname
            username: SSH username
            password: SSH password
            docker_image: Docker image to deploy
            worker_name: Name for the worker service
            replica_count: Number of replicas to deploy
            
        Returns:
            Tuple of (success, result_data, error_message)
        """
        try:
            import paramiko
            
            logger.info(f"Launching worker {worker_name} on {host}")
            
            # Create SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to remote host
            ssh.connect(host, username=username, password=password, timeout=30)
            logger.debug(f"Connected to {host} via SSH")
            
            # Get swarm nodes
            success, nodes, error = self.list_nodes()
            if not success:
                return False, {}, f"Failed to get swarm info: {error}"
            
            # Check if this is the manager
            is_manager = any(n.is_manager for n in nodes)
            if not is_manager:
                return False, {}, "Current node is not a swarm manager"
            
            # Get worker join token from manager
            try:
                result = subprocess.run(
                    ['docker', 'swarm', 'join-token', 'worker', '-q'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0:
                    return False, {}, f"Failed to get join token: {result.stderr}"
                join_token = result.stdout.strip()
            except Exception as e:
                return False, {}, f"Failed to get join token: {str(e)}"
            
            # Get manager IP
            manager_ip = None
            for node in nodes:
                if node.is_manager:
                    manager_ip = node.ip_address
                    break
            
            if not manager_ip:
                return False, {}, "Could not determine manager IP address"
            
            logger.debug(f"Manager IP: {manager_ip}, Join token: {join_token[:20]}...")
            
            # Prepare Docker Swarm join command
            join_cmd = f"docker swarm join --token {join_token} {manager_ip}:2377"
            
            # Execute commands on remote host
            commands = [
                ("echo 'Joining Docker Swarm...'", "info"),
                (join_cmd, "join"),
                ("sleep 2", "wait"),
                (f"docker pull {docker_image}", "pull"),
                (f"docker run -d --name {worker_name}-check {docker_image} echo 'Test'", "test"),
                (f"docker rm -f {worker_name}-check 2>/dev/null || true", "cleanup"),
            ]
            
            execution_log = []
            for cmd, step in commands:
                logger.debug(f"Executing on {host}: {cmd}")
                stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
                exit_code = stdout.channel.recv_exit_status()
                
                output = stdout.read().decode('utf-8', errors='ignore').strip()
                error_output = stderr.read().decode('utf-8', errors='ignore').strip()
                
                execution_log.append({
                    "step": step,
                    "command": cmd,
                    "exit_code": exit_code,
                    "output": output[:200] if output else "",
                    "error": error_output[:200] if error_output else ""
                })
                
                logger.debug(f"Step {step} - Exit code: {exit_code}")
                if exit_code != 0 and step not in ["cleanup"]:
                    ssh.close()
                    error_msg = f"Failed at step {step}: {error_output}"
                    logger.error(error_msg)
                    return False, {"execution_log": execution_log}, error_msg
            
            ssh.close()
            
            # Wait for node to appear in swarm
            import time
            max_retries = 30
            for i in range(max_retries):
                success, nodes, _ = self.get_swarm_nodes()
                if success and len(nodes) > 1:
                    logger.info(f"New worker node appeared after {i} retries")
                    new_node = [n for n in nodes if n.ip_address != manager_ip]
                    if new_node:
                        new_node = new_node[0]
                        return True, {
                            "worker_name": worker_name,
                            "host": host,
                            "node_id": new_node.id,
                            "hostname": new_node.hostname,
                            "status": new_node.status,
                            "availability": new_node.availability,
                            "execution_log": execution_log
                        }, ""
                time.sleep(1)
            
            logger.warning(f"New worker node did not appear after {max_retries} seconds")
            return True, {
                "worker_name": worker_name,
                "host": host,
                "status": "joined_but_not_visible",
                "execution_log": execution_log
            }, "Worker joined but not visible in swarm yet"
            
        except ImportError:
            return False, {}, "paramiko library not installed. Run: pip install paramiko"
        except Exception as e:
            error_msg = f"Failed to launch remote worker: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, {}, error_msg


# Create singleton instance
_swarm_service = None


def get_swarm_service() -> DockerSwarmService:
    """Get or create swarm service instance"""
    global _swarm_service
    if _swarm_service is None:
        _swarm_service = DockerSwarmService()
    return _swarm_service
