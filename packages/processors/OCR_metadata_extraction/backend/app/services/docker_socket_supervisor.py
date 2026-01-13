"""
Docker Socket-based Supervisor Service
Uses Docker API instead of SSH for remote worker management
No OS-level complexity, direct Docker communication
"""

import docker
import json
import logging
import time
import shlex
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RemoteDocker:
    """Configuration for remote Docker daemon via socket"""
    host: str
    port: int = 2375
    use_tls: bool = False
    verify_tls: bool = False
    
    @property
    def base_url(self) -> str:
        protocol = "https" if self.use_tls else "tcp"
        return f"{protocol}://{self.host}:{self.port}"


class DockerSocketSupervisor:
    """
    Manages remote worker deployments via Docker API
    
    No SSH, no shell profiles, no PATH issues
    Direct communication with Docker daemon
    """
    
    def __init__(self, remote_docker: RemoteDocker):
        self.remote_docker = remote_docker
        self.client = None
        self.logger = logger
        
    def connect(self) -> bool:
        """Connect to remote Docker daemon"""
        try:
            self.client = docker.DockerClient(
                base_url=self.remote_docker.base_url,
                timeout=10
            )
            # Test connection
            self.client.ping()
            self.logger.info(f"✓ Connected to Docker at {self.remote_docker.base_url}")
            return True
        except Exception as e:
            self.logger.error(f"✗ Failed to connect to Docker: {str(e)}")
            return False
    
    def pull_image(self, image: str) -> bool:
        """Pull Docker image from registry with progress tracking"""
        try:
            self.logger.info(f"📥 Pulling image: {image}")
            
            # Pull with streaming to track progress
            for line in self.client.api.pull(image, stream=True, decode=True):
                if 'status' in line:
                    status = line['status']
                    if 'progress' in line:
                        self.logger.debug(f"  {status} {line.get('progress', '')}")
                    else:
                        self.logger.info(f"  {status}")
                
                if 'error' in line:
                    error = line['error']
                    self.logger.error(f"✗ Pull error: {error}")
                    return False
            
            self.logger.info(f"✓ Successfully pulled image: {image}")
            return True
        except Exception as e:
            self.logger.error(f"✗ Failed to pull image {image}: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def deploy_workers(self, 
                      image: str,
                      count: int = 1,
                      environment: Dict = None,
                      volumes: Dict = None,
                      network: str = None,
                      command: str = None) -> List[str]:
        """
        Deploy worker containers
        
        Args:
            image: Docker image name (e.g., 'registry.docgenai.com:5010/gvpocr-worker:latest')
            count: Number of worker containers
            environment: Environment variables dict
            volumes: Volumes dict {'/app/Bhushanji': {'bind': '/mnt/bhushanji', 'mode': 'ro'}}
            network: Network name to connect to
            command: Command to run in container (e.g., 'python run_worker.py --worker-id 0 --nsqlookupd ...')
            
        Returns:
            List of container IDs
        """
        try:
            # Pull image first
            if not self.pull_image(image):
                raise Exception(f"Failed to pull image: {image}")
            
            container_ids = []
            for i in range(count):
                container_name = f"gvpocr-worker-{i}"
                
                # Remove existing container with same name
                try:
                    existing = self.client.containers.get(container_name)
                    self.logger.info(f"Removing existing container: {container_name}")
                    existing.stop(timeout=5)
                    existing.remove(force=True)
                    self.logger.info(f"✓ Removed existing {container_name}")
                except docker.errors.NotFound:
                    pass  # Container doesn't exist, continue
                except Exception as e:
                    self.logger.warning(f"Could not remove existing container {container_name}: {str(e)}")
                
                self.logger.info(f"Starting container: {container_name}")
                
                # Build the command if provided
                # Command should already have {worker_id} replaced by caller
                container_command = None
                if command:
                    # If command is a string, convert to list
                    if isinstance(command, str):
                        container_command = shlex.split(command)
                    else:
                        container_command = command
                    self.logger.info(f"Container command: {container_command}")
                
                container = self.client.containers.run(
                    image,
                    container_command,
                    name=container_name,
                    detach=True,
                    environment=environment or {},
                    volumes=volumes or {},
                    network=network,
                    restart_policy={'Name': 'unless-stopped'}
                )
                
                container_ids.append(container.id)
                self.logger.info(f"✓ Started {container_name}: {container.id[:12]}")
            
            return container_ids
            
        except Exception as e:
            self.logger.error(f"✗ Failed to deploy workers: {str(e)}", exc_info=True)
            raise  # Re-raise to let caller handle with context
    
    def stop_workers(self, container_ids: List[str] = None) -> bool:
        """
        Stop worker containers
        
        Args:
            container_ids: List of container IDs. If None, stops all 'gvpocr-worker*' containers
        """
        try:
            if not container_ids:
                # Stop all gvpocr-worker containers
                containers = self.client.containers.list(
                    filters={'name': 'gvpocr-worker'}
                )
                container_ids = [c.id for c in containers]
            
            for container_id in container_ids:
                container = self.client.containers.get(container_id)
                container.stop(timeout=10)
                self.logger.info(f"✓ Stopped {container.name}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"✗ Failed to stop workers: {str(e)}")
            return False
    
    def remove_workers(self, container_ids: List[str] = None) -> bool:
        """
        Remove worker containers
        
        Args:
            container_ids: List of container IDs. If None, removes all 'gvpocr-worker*' containers
        """
        try:
            if not container_ids:
                containers = self.client.containers.list(
                    all=True,
                    filters={'name': 'gvpocr-worker'}
                )
                container_ids = [c.id for c in containers]
            
            for container_id in container_ids:
                try:
                    container = self.client.containers.get(container_id)
                    container.stop(timeout=5)
                    container.remove(force=True)
                    self.logger.info(f"✓ Removed {container.name}")
                except Exception as e:
                    self.logger.warning(f"Could not remove {container_id}: {str(e)}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"✗ Failed to remove workers: {str(e)}")
            return False
    
    def restart_workers(self, container_ids: List[str] = None) -> bool:
        """
        Restart worker containers
        
        Args:
            container_ids: List of container IDs. If None, restarts all 'gvpocr-worker*' containers
        """
        try:
            if not container_ids:
                containers = self.client.containers.list(
                    filters={'name': 'gvpocr-worker'}
                )
                container_ids = [c.id for c in containers]
            
            for container_id in container_ids:
                container = self.client.containers.get(container_id)
                container.restart(timeout=10)
                self.logger.info(f"✓ Restarted {container.name}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"✗ Failed to restart workers: {str(e)}")
            return False
    
    def get_container_status(self) -> Dict:
        """Get status of all gvpocr-worker containers"""
        try:
            containers = self.client.containers.list(
                all=True,
                filters={'name': 'gvpocr-worker'}
            )
            
            status_list = []
            for container in containers:
                status_list.append({
                    'id': container.id[:12],
                    'name': container.name,
                    'status': container.status,
                    'image': container.image.tags[0] if container.image.tags else 'unknown',
                    'cpu_percent': self._get_cpu_percent(container),
                    'memory_usage': self._get_memory_usage(container)
                })
            
            return {
                'total': len(status_list),
                'containers': status_list
            }
            
        except Exception as e:
            self.logger.error(f"✗ Failed to get container status: {str(e)}")
            return {'total': 0, 'containers': [], 'error': str(e)}
    
    def _get_cpu_percent(self, container) -> str:
        """Get CPU usage percentage"""
        try:
            stats = container.stats(stream=False)
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            cpu_percent = (cpu_delta / system_delta) * 100.0
            return f"{cpu_percent:.1f}%"
        except:
            return "N/A"
    
    def _get_memory_usage(self, container) -> str:
        """Get memory usage in MB"""
        try:
            stats = container.stats(stream=False)
            memory_usage = stats['memory_stats']['usage'] / (1024 * 1024)
            memory_limit = stats['memory_stats']['limit'] / (1024 * 1024)
            return f"{memory_usage:.1f}MB / {memory_limit:.1f}MB"
        except:
            return "N/A"
    
    def get_logs(self, container_name: str = None, tail: int = 100) -> str:
        """
        Get container logs
        
        Args:
            container_name: Specific container name. If None, returns logs from all workers
            tail: Number of lines to return
        """
        try:
            if container_name:
                container = self.client.containers.get(container_name)
                logs = container.logs(tail=tail).decode('utf-8')
            else:
                # Get logs from all workers
                containers = self.client.containers.list(
                    filters={'name': 'gvpocr-worker'}
                )
                logs = ""
                for container in containers:
                    logs += f"\n===== {container.name} =====\n"
                    logs += container.logs(tail=tail).decode('utf-8')
            
            return logs
            
        except Exception as e:
            self.logger.error(f"✗ Failed to get logs: {str(e)}")
            return f"Error getting logs: {str(e)}"
    
    def stream_logs(self, container_name: str = None, tail: int = 50):
        """
        Stream container logs (generator for real-time updates)
        
        Args:
            container_name: Specific container name. If None, streams from first worker
            tail: Initial lines to return
        """
        try:
            if not container_name:
                containers = self.client.containers.list(
                    filters={'name': 'gvpocr-worker'}
                )
                if containers:
                    container_name = containers[0].name
                else:
                    yield "No running workers found"
                    return
            
            container = self.client.containers.get(container_name)
            
            # Stream logs with heartbeat to prevent timeout
            for line in container.logs(stream=True, follow=True, tail=tail):
                decoded_line = line.decode('utf-8').rstrip()
                if decoded_line:
                    yield decoded_line + '\n'
                
        except docker.errors.NotFound:
            yield f"Container not found: {container_name}\n"
        except Exception as e:
            self.logger.error(f"Error streaming logs: {str(e)}")
            yield f"Error streaming logs: {str(e)}\n"
    
    def pull_image(self, image: str) -> bool:
        """Pull Docker image from registry"""
        try:
            self.logger.info(f"Pulling image: {image}")
            self.client.images.pull(image)
            self.logger.info(f"✓ Image pulled successfully: {image}")
            return True
        except Exception as e:
            self.logger.error(f"✗ Failed to pull image {image}: {str(e)}")
            return False
    
    def push_image(self, image: str, registry: str = None) -> bool:
        """Push Docker image to registry"""
        try:
            if registry:
                full_image = f"{registry}/{image}"
                self.client.images.get(image).tag(full_image)
            else:
                full_image = image
            
            self.logger.info(f"Pushing image: {full_image}")
            self.client.images.push(full_image)
            self.logger.info(f"✓ Image pushed successfully: {full_image}")
            return True
        except Exception as e:
            self.logger.error(f"✗ Failed to push image {full_image}: {str(e)}")
            return False
    
    def scale_workers(self, target_count: int, 
                     image: str,
                     environment: Dict = None,
                     volumes: Dict = None,
                     network: str = None) -> Tuple[bool, str, int]:
        """
        Scale worker containers to target count
        
        Args:
            target_count: Desired number of worker containers
            image: Docker image to use for new containers
            environment: Environment variables
            volumes: Volume mounts
            network: Network name
            
        Returns:
            Tuple of (success, message, current_count)
        """
        try:
            # Get current containers
            containers = self.client.containers.list(
                filters={'name': 'gvpocr-worker'}
            )
            current_count = len(containers)
            
            if current_count == target_count:
                return True, f"Already at target count: {target_count}", target_count
            elif current_count < target_count:
                # Scale up
                new_containers = target_count - current_count
                self.logger.info(f"Scaling up: adding {new_containers} workers")
                
                created_ids = self.deploy_workers(
                    image=image,
                    count=new_containers,
                    environment=environment,
                    volumes=volumes,
                    network=network
                )
                
                if created_ids:
                    return True, f"Scaled up from {current_count} to {target_count}", target_count
                else:
                    return False, "Failed to scale up", current_count
            else:
                # Scale down
                to_remove = current_count - target_count
                self.logger.info(f"Scaling down: removing {to_remove} workers")
                
                container_ids = [c.id for c in containers[:to_remove]]
                if self.remove_workers(container_ids):
                    return True, f"Scaled down from {current_count} to {target_count}", target_count
                else:
                    return False, "Failed to scale down", current_count
                    
        except Exception as e:
            self.logger.error(f"✗ Failed to scale workers: {str(e)}")
            return False, f"Scale failed: {str(e)}", 0
    
    def health_check(self) -> Dict:
        """Perform health check on remote Docker"""
        try:
            info = self.client.info()
            return {
                'healthy': True,
                'docker_version': info['ServerVersion'],
                'containers': info['Containers'],
                'images': info['Images'],
                'memory_available': info['MemTotal'] / (1024**3),  # GB
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }


# Example usage
if __name__ == '__main__':
    # Test locally
    remote = RemoteDocker(host='localhost', port=2375)
    supervisor = DockerSocketSupervisor(remote)
    
    if supervisor.connect():
        print("✓ Connected to Docker")
        print(supervisor.health_check())
        print(supervisor.get_container_status())
    else:
        print("✗ Failed to connect")
