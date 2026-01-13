"""
Routes for remote worker supervisor management

Provides API endpoints for deploying, monitoring, and managing remote OCR workers via SSH.
"""
from flask import Blueprint, jsonify, request, Response
from app.services.supervisor_service import SupervisorService
from app.models.worker_deployment import WorkerDeployment
from app.utils.decorators import token_required, token_required_sse
from app.models import mongo
import logging
import json
import threading
import time


logger = logging.getLogger(__name__)

supervisor_bp = Blueprint('supervisor', __name__, url_prefix='/api/supervisor')


def _deploy_worker_async(deployment_id: str, deployment_config: dict, current_user_id: str):
    """
    Background task to deploy worker without blocking HTTP response
    
    Updates deployment status in database as progress changes
    """
    try:
        logger.info(f"Starting async deployment for {deployment_id}")
        
        supervisor = SupervisorService()
        result = supervisor.deploy_worker(deployment_config)
        
        if result.get('success'):
            logger.info(f"Deployment {deployment_id} successful")
            WorkerDeployment.update_status(mongo, deployment_id, 'running')
            
            if 'containers' in result:
                WorkerDeployment.update_containers(mongo, deployment_id, result['containers'])
            
            # Perform initial health check
            time.sleep(2)  # Wait for containers to stabilize
            try:
                deployment = WorkerDeployment.find_by_id(mongo, deployment_id, current_user_id)
                if deployment:
                    health_data = supervisor.check_worker_health(deployment)
                    WorkerDeployment.update_health(mongo, deployment_id, health_data)
                    logger.info(f"Initial health check for {deployment_id}: {health_data.get('health_status')}")
            except Exception as e:
                logger.warning(f"Initial health check failed for {deployment_id}: {str(e)}")
        else:
            logger.error(f"Deployment {deployment_id} failed: {result.get('error')}")
            WorkerDeployment.update_status(
                mongo,
                deployment_id,
                'error',
                error_message=result.get('error', 'Deployment failed')
            )
    except Exception as e:
        logger.error(f"Async deployment error for {deployment_id}: {str(e)}", exc_info=True)
        WorkerDeployment.update_status(
            mongo,
            deployment_id,
            'error',
            error_message=str(e)
        )


@supervisor_bp.route('/deployments', methods=['GET'])
@token_required
def get_deployments(current_user_id):
    """
    Get all worker deployments for current user

    Returns:
        JSON response with list of deployments
    """
    try:
        deployments = WorkerDeployment.find_by_user(mongo, current_user_id)

        return jsonify({
            'success': True,
            'deployments': [WorkerDeployment.to_dict(d) for d in deployments],
            'count': len(deployments)
        }), 200

    except Exception as e:
        logger.error(f"Error fetching deployments: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@supervisor_bp.route('/config/defaults', methods=['GET'])
@token_required
def get_default_config(current_user_id):
    """
    Get default configuration values for worker deployment

    Returns default values for NSQ, MongoDB, and server URL based on environment
    """
    import os
    from urllib.parse import quote_plus

    try:
        # Get main server IP (from nsqd broadcast address or default)
        main_server_ip = os.getenv('MAIN_SERVER_IP', '172.12.0.132')

        # Build MongoDB URI with credentials
        mongo_username = os.getenv('MONGO_USERNAME', 'gvpocr_admin')
        mongo_password = os.getenv('MONGO_PASSWORD', '')
        encoded_password = quote_plus(mongo_password) if mongo_password else mongo_password

        mongo_uri = f"mongodb://{mongo_username}:{encoded_password}@{main_server_ip}:27017/gvpocr?authSource=admin"

        return jsonify({
            'success': True,
            'config': {
                'nsqd_address': f'{main_server_ip}:4150',
                'nsqlookupd_addresses': f'{main_server_ip}:4161',
                'mongo_uri': mongo_uri,
                'server_url': f'http://{main_server_ip}:5000'
            }
        }), 200

    except Exception as e:
        logger.error(f"Error fetching default config: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@supervisor_bp.route('/deployments', methods=['POST'])
@token_required
def create_deployment(current_user_id):
    """
    Deploy new worker to remote host (async)

    Returns immediately with deployment ID. Actual deployment happens in background.
    Poll /api/supervisor/deployments/<deployment_id> to check status.

    Request Body:
    {
        "worker_name": "Production Worker 1",
        "host": "192.168.1.100",
        "port": 22,
        "username": "ubuntu",
        "ssh_key_name": "production_key",
        "worker_count": 2,
        "nsqd_address": "10.0.0.5:4150",
        "nsqlookupd_addresses": ["10.0.0.5:4161"],
        "mongo_uri": "mongodb://10.0.0.5:27017/gvpocr",
        "server_url": "http://10.0.0.5:5000",
        "providers": {
            "google_vision_enabled": true,
            "tesseract_enabled": true
        }
    }

    Returns:
        JSON response with deployment record (status will be 'deploying')
    """
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = [
            'worker_name', 'host', 'username', 'ssh_key_name',
            'nsqd_address', 'nsqlookupd_addresses', 'mongo_uri', 'server_url'
        ]

        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Add Docker Socket configuration (optional, defaults to auto-detect)
        # If 'use_docker_socket' is not specified, the supervisor will try Docker Socket first
        if 'use_docker_socket' not in data:
            data['use_docker_socket'] = True  # Try Docker Socket by default
        
        if 'docker_socket_port' not in data:
            data['docker_socket_port'] = 2375  # Default Docker Socket TCP port
        
        # Ensure host is IP address (not hostname) for Docker Socket connection
        if 'docker_socket_host' not in data:
            data['docker_socket_host'] = data.get('host', 'localhost')

        # Set deployment type - used to determine how to interact with the deployment (SSH vs Docker Socket)
        if 'deployment_type' not in data:
            data['deployment_type'] = 'docker_socket' if data.get('use_docker_socket') else 'ssh'

        # Create deployment record in database
        deployment = WorkerDeployment.create(mongo, current_user_id, data)
        deployment_id = str(deployment['_id'])

        logger.info(f"Created deployment record: {deployment_id}")

        # Prepare config for async task
        deployment_config = dict(data)
        deployment_config['worker_id'] = deployment['worker_id']

        # Start deployment in background thread (non-blocking)
        thread = threading.Thread(
            target=_deploy_worker_async,
            args=(deployment_id, deployment_config, current_user_id),
            daemon=True
        )
        thread.start()
        logger.info(f"Started background deployment thread for {deployment_id}")

        # Return immediately with status 'deploying'
        return jsonify({
            'success': True,
            'message': 'Deployment started. Use /api/supervisor/deployments/<id> to check status.',
            'deployment': WorkerDeployment.to_dict(deployment)
        }), 202  # 202 Accepted - request accepted but processing

    except Exception as e:
        logger.error(f"Error creating deployment: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@supervisor_bp.route('/deployments/<deployment_id>', methods=['GET'])
@token_required
def get_deployment(current_user_id, deployment_id):
    """
    Get specific deployment details

    Args:
        deployment_id: Deployment ID

    Returns:
        JSON response with deployment details
    """
    try:
        deployment = WorkerDeployment.find_by_id(mongo, deployment_id, current_user_id)

        if not deployment:
            return jsonify({
                'success': False,
                'error': 'Deployment not found'
            }), 404

        # Update last accessed
        WorkerDeployment.update_last_accessed(mongo, deployment_id)

        return jsonify({
            'success': True,
            'deployment': WorkerDeployment.to_dict(deployment)
        }), 200

    except Exception as e:
        logger.error(f"Error fetching deployment: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@supervisor_bp.route('/deployments/<deployment_id>/start', methods=['POST'])
@token_required
def start_deployment(current_user_id, deployment_id):
    """
    Start workers on deployment

    Args:
        deployment_id: Deployment ID

    Returns:
        JSON response with operation result
    """
    try:
        deployment = WorkerDeployment.find_by_id(mongo, deployment_id, current_user_id)

        if not deployment:
            return jsonify({
                'success': False,
                'error': 'Deployment not found'
            }), 404

        supervisor = SupervisorService()
        success, error_message = supervisor.start_workers(deployment)

        if success:
            WorkerDeployment.update_status(mongo, deployment_id, 'running')
            return jsonify({
                'success': True,
                'message': 'Workers started successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': error_message or 'Failed to start workers'
            }), 500

    except Exception as e:
        logger.error(f"Error starting deployment: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@supervisor_bp.route('/deployments/<deployment_id>/stop', methods=['POST'])
@token_required
def stop_deployment(current_user_id, deployment_id):
    """
    Stop workers on deployment

    Args:
        deployment_id: Deployment ID

    Returns:
        JSON response with operation result
    """
    try:
        deployment = WorkerDeployment.find_by_id(mongo, deployment_id, current_user_id)

        if not deployment:
            return jsonify({
                'success': False,
                'error': 'Deployment not found'
            }), 404

        supervisor = SupervisorService()
        success, error_message = supervisor.stop_workers(deployment)

        if success:
            WorkerDeployment.update_status(mongo, deployment_id, 'stopped')
            return jsonify({
                'success': True,
                'message': 'Workers stopped successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': error_message or 'Failed to stop workers'
            }), 500

    except Exception as e:
        logger.error(f"Error stopping deployment: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@supervisor_bp.route('/deployments/<deployment_id>/restart', methods=['POST'])
@token_required
def restart_deployment(current_user_id, deployment_id):
    """
    Restart workers on deployment

    Args:
        deployment_id: Deployment ID

    Returns:
        JSON response with operation result
    """
    try:
        deployment = WorkerDeployment.find_by_id(mongo, deployment_id, current_user_id)

        if not deployment:
            return jsonify({
                'success': False,
                'error': 'Deployment not found'
            }), 404

        supervisor = SupervisorService()
        success, error_message = supervisor.restart_workers(deployment)

        if success:
            WorkerDeployment.update_status(mongo, deployment_id, 'running')
            return jsonify({
                'success': True,
                'message': 'Workers restarted successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': error_message or 'Failed to restart workers'
            }), 500

    except Exception as e:
        logger.error(f"Error restarting deployment: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@supervisor_bp.route('/deployments/<deployment_id>/update-image', methods=['POST'])
@token_required
def update_docker_image(current_user_id, deployment_id):
    """
    Update Docker image on worker deployment
    
    Pulls latest image from registry and rebuilds containers

    Args:
        deployment_id: Deployment ID

    Returns:
        JSON response with operation result
    """
    try:
        deployment = WorkerDeployment.find_by_id(mongo, deployment_id, current_user_id)

        if not deployment:
            logger.warning(f"Deployment {deployment_id} not found for user {current_user_id}")
            return jsonify({
                'success': False,
                'error': 'Deployment not found'
            }), 404

        logger.info(f"🔄 Starting Docker image update for deployment: {deployment_id}")
        logger.info(f"   Host: {deployment.get('host')}, Worker: {deployment.get('worker_name')}")
        
        supervisor = SupervisorService()
        success, error_message = supervisor.update_docker_image(deployment)

        if success:
            logger.info(f"✅ Docker image updated successfully for deployment: {deployment_id}")
            return jsonify({
                'success': True,
                'message': 'Docker image updated successfully'
            }), 200
        else:
            logger.error(f"❌ Failed to update Docker image: {error_message}")
            return jsonify({
                'success': False,
                'error': error_message or 'Failed to update Docker image'
            }), 500

    except Exception as e:
        logger.error(f"Error updating Docker image: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@supervisor_bp.route('/deployments/<deployment_id>/scale', methods=['POST'])
@token_required
def scale_deployment(current_user_id, deployment_id):
    """
    Scale worker count up or down

    Args:
        deployment_id: Deployment ID

    Request Body:
    {
        "worker_count": 4
    }

    Returns:
        JSON response with operation result
    """
    try:
        deployment = WorkerDeployment.find_by_id(mongo, deployment_id, current_user_id)

        if not deployment:
            return jsonify({
                'success': False,
                'error': 'Deployment not found'
            }), 404

        data = request.get_json()
        worker_count = data.get('worker_count')

        if not worker_count or worker_count < 1:
            return jsonify({
                'success': False,
                'error': 'Invalid worker_count. Must be >= 1'
            }), 400

        supervisor = SupervisorService()
        success = supervisor.scale_workers(deployment, worker_count)

        if success:
            WorkerDeployment.update_worker_count(mongo, deployment_id, worker_count)
            return jsonify({
                'success': True,
                'message': f'Scaled to {worker_count} worker(s) successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to scale workers'
            }), 500

    except Exception as e:
        logger.error(f"Error scaling deployment: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@supervisor_bp.route('/deployments/<deployment_id>', methods=['DELETE'])
@token_required
def delete_deployment(current_user_id, deployment_id):
    """
    Remove worker deployment

    Args:
        deployment_id: Deployment ID

    Returns:
        JSON response with operation result
    """
    try:
        deployment = WorkerDeployment.find_by_id(mongo, deployment_id, current_user_id)

        if not deployment:
            return jsonify({
                'success': False,
                'error': 'Deployment not found'
            }), 404

        # Remove workers via SSH
        supervisor = SupervisorService()
        success = supervisor.remove_workers(deployment)

        if not success:
            return jsonify({
                'success': False,
                'error': 'Failed to remove workers. Check network connection and SSH access.'
            }), 500

        # Delete deployment record
        WorkerDeployment.delete(mongo, deployment_id, current_user_id)

        return jsonify({
            'success': True,
            'message': 'Deployment removed successfully'
        }), 200

    except Exception as e:
        logger.error(f"Error deleting deployment: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@supervisor_bp.route('/deployments/<deployment_id>/health', methods=['GET'])
@token_required
def check_health(current_user_id, deployment_id):
    """
    Get health status of deployment

    Args:
        deployment_id: Deployment ID

    Returns:
        JSON response with health data
    """
    try:
        deployment = WorkerDeployment.find_by_id(mongo, deployment_id, current_user_id)

        if not deployment:
            return jsonify({
                'success': False,
                'error': 'Deployment not found'
            }), 404

        supervisor = SupervisorService()
        health_data = supervisor.check_worker_health(deployment)

        # Update health in database
        WorkerDeployment.update_health(mongo, deployment_id, health_data)

        return jsonify({
            'success': True,
            'health': health_data
        }), 200

    except Exception as e:
        logger.error(f"Error checking health: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@supervisor_bp.route('/deployments/<deployment_id>/stats', methods=['GET'])
@token_required
def get_stats(current_user_id, deployment_id):
    """
    Get detailed statistics for deployment

    Args:
        deployment_id: Deployment ID

    Returns:
        JSON response with statistics
    """
    try:
        deployment = WorkerDeployment.find_by_id(mongo, deployment_id, current_user_id)

        if not deployment:
            return jsonify({
                'success': False,
                'error': 'Deployment not found'
            }), 404

        supervisor = SupervisorService()
        stats = supervisor.get_worker_stats(deployment)

        return jsonify({
            'success': True,
            'stats': stats
        }), 200

    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@supervisor_bp.route('/deployments/<deployment_id>/logs', methods=['GET'])
@token_required
def get_logs(current_user_id, deployment_id):
    """
    Get container logs

    Args:
        deployment_id: Deployment ID

    Query params:
        - container_name: Name of specific container (optional - if not provided, gets all docker-compose logs)
        - lines: Number of lines (default 100)

    Returns:
        JSON response with logs
    """
    try:
        deployment = WorkerDeployment.find_by_id(mongo, deployment_id, current_user_id)

        if not deployment:
            return jsonify({
                'success': False,
                'error': 'Deployment not found'
            }), 404

        container_name = request.args.get('container_name')
        lines = int(request.args.get('lines', 100))

        supervisor = SupervisorService()
        logs = supervisor.get_container_logs(deployment, container_name, lines)

        return jsonify({
            'success': True,
            'logs': logs,
            'container_name': container_name or 'all'
        }), 200

    except Exception as e:
        logger.error(f"Error getting logs: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@supervisor_bp.route('/deployments/<deployment_id>/logs/stream', methods=['GET'])
@token_required_sse
def stream_logs(current_user_id, deployment_id):
    """
    Stream container logs via Server-Sent Events (SSE)

    Args:
        deployment_id: Deployment ID

    Query params:
        - container_name: Name of specific container (optional - if not provided, streams all docker-compose logs)

    Returns:
        SSE stream of log lines
    """
    deployment = WorkerDeployment.find_by_id(mongo, deployment_id, current_user_id)

    if not deployment:
        def error_gen():
            yield f"data: {json.dumps({'error': 'Deployment not found'})}\n\n"
        return Response(error_gen(), mimetype='text/event-stream')

    container_name = request.args.get('container_name')

    def generate():
        """Generator function for SSE"""
        try:
            supervisor = SupervisorService()

            # Send initial connection message
            container_label = container_name or 'all'
            yield f"data: {json.dumps({'status': 'connected', 'container': container_label})}\n\n"

            # Stream logs
            for log_line in supervisor.stream_container_logs(deployment, container_name):
                yield f"data: {json.dumps({'log': log_line})}\n\n"

        except Exception as e:
            logger.error(f"Error streaming logs: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype='text/event-stream')


@supervisor_bp.route('/nsq/stats', methods=['GET'])
@token_required
def get_nsq_stats(current_user_id):
    """
    Get NSQ queue statistics

    Returns:
        JSON response with NSQ statistics
    """
    try:
        from app.services.nsq_service import NSQService

        nsq_service = NSQService()
        topic_stats = nsq_service.get_topic_stats('bulk_ocr_file_tasks')

        if not topic_stats:
            return jsonify({
                'success': False,
                'error': 'Unable to retrieve NSQ statistics'
            }), 503

        return jsonify({
            'success': True,
            'stats': topic_stats
        }), 200

    except Exception as e:
        logger.error(f"Error getting NSQ stats: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@supervisor_bp.route('/ssh-keys', methods=['GET'])
@token_required
def list_ssh_keys(current_user_id):
    """
    List available SSH keys for deployment

    Returns:
        JSON response with list of SSH key names
    """
    try:
        supervisor = SupervisorService()
        keys = supervisor.list_available_ssh_keys()

        return jsonify({
            'success': True,
            'ssh_keys': keys
        }), 200

    except Exception as e:
        logger.error(f"Error listing SSH keys: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@supervisor_bp.route('/test-connection', methods=['POST'])
@token_required
def test_connection(current_user_id):
    """
    Test SSH connectivity before deployment

    Request Body:
    {
        "host": "192.168.1.100",
        "port": 22,
        "username": "ubuntu",
        "ssh_key_name": "production_key"
    }

    Returns:
        JSON response with connection test result
    """
    try:
        data = request.get_json()

        required_fields = ['host', 'username', 'ssh_key_name']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400

        host = data['host']
        port = data.get('port', 22)
        username = data['username']
        ssh_key_name = data['ssh_key_name']

        supervisor = SupervisorService()
        result = supervisor.test_ssh_connectivity(host, port, username, ssh_key_name)

        return jsonify(result), 200 if result.get('success') else 500

    except Exception as e:
        logger.error(f"Error testing connection: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@supervisor_bp.route('/build-push-worker', methods=['GET'])
@token_required_sse
def build_push_worker(current_user_id):
    """
    Build worker Docker image and push to registry
    Streams progress updates via Server-Sent Events
    
    Returns:
        Server-Sent Events stream with progress updates
    """
    def stream_build_progress():
        import subprocess
        import os
        
        try:
            yield f'data: {json.dumps({"status": "Starting Docker build..."})}\n\n'
            
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            
            # Build the Docker image with progress
            yield f'data: {json.dumps({"progress": 10, "status": "Building Docker image..."})}\n\n'
            
            build_cmd = [
                '/usr/bin/docker', 'build',
                '-f', os.path.join(project_root, 'worker.Dockerfile'),
                '-t', 'registry.docgenai.com:5010/gvpocr-worker-updated:latest',
                '--progress=plain',
                project_root
            ]
            
            proc = subprocess.Popen(build_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            build_steps = 0
            
            for line in proc.stdout:
                line = line.strip()
                if line:
                    logger.info(f"Build: {line}")
                    yield f'data: {json.dumps({"log": line})}\n\n'
                    
                    if 'Step' in line:
                        build_steps += 1
                        progress = min(10 + (build_steps * 3), 55)
                        yield f'data: {json.dumps({"progress": progress, "status": f"Building step {build_steps}..."})}\n\n'
            
            proc.wait()
            
            if proc.returncode != 0:
                error_msg = f'Build failed with exit code {proc.returncode}'
                logger.error(error_msg)
                yield f'data: {json.dumps({"error": error_msg})}\n\n'
                return
            
            yield f'data: {json.dumps({"progress": 60, "status": "Build completed. Pushing to registry..."})}\n\n'
            
            # Push the image to registry with progress
            push_cmd = [
                '/usr/bin/docker', 'push',
                'registry.docgenai.com:5010/gvpocr-worker-updated:latest'
            ]
            
            proc = subprocess.Popen(push_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            push_steps = 0
            
            for line in proc.stdout:
                line = line.strip()
                if line:
                    logger.info(f"Push: {line}")
                    yield f'data: {json.dumps({"log": line})}\n\n'
                    
                    if any(x in line for x in ['Pushing', 'Pushed', 'digest']):
                        push_steps += 1
                        progress = min(60 + (push_steps * 8), 99)
                        yield f'data: {json.dumps({"progress": progress, "status": f"Pushing layers ({push_steps})..."})}\n\n'
            
            proc.wait()
            
            if proc.returncode != 0:
                error_msg = f'Push failed with exit code {proc.returncode}'
                logger.error(error_msg)
                yield f'data: {json.dumps({"error": error_msg})}\n\n'
                return
            
            yield f'data: {json.dumps({"progress": 100, "status": "Image successfully pushed to registry!"})}\n\n'
            yield f'data: {json.dumps({"success": true})}\n\n'
            
        except subprocess.TimeoutExpired:
            yield f'data: {json.dumps({"error": "Build/push operation timed out"})}\n\n'
        except Exception as e:
            logger.error(f"Build/push error: {str(e)}", exc_info=True)
            yield f'data: {json.dumps({"error": f"Build/push failed: {str(e)}"})}\n\n'
    
    return Response(stream_build_progress(), mimetype='text/event-stream',
                   headers={
                       'Cache-Control': 'no-cache',
                       'X-Accel-Buffering': 'no'
                   })


def _build_worker_env(deployment):
    """Build environment variables from deployment config"""
    env = {
        'WORKER_ID': deployment.get('worker_id'),
        'NSQD_ADDRESS': deployment.get('nsqd_address'),
        'NSQLOOKUPD_ADDRESSES': ','.join(deployment.get('nsqlookupd_addresses', [])),
        'MONGO_URI': deployment.get('mongo_uri'),
        'SERVER_URL': deployment.get('server_url'),
    }
    
    # Add provider settings
    providers = deployment.get('providers', {})
    for key, value in providers.items():
        env[f'PROVIDER_{key.upper()}'] = str(value)
    
    return env


def _build_worker_volumes(deployment):
    """Build volume mounts from deployment config"""
    volumes = {
        '/app/Bhushanji': {
            'bind': '/mnt/bhushanji',
            'mode': 'ro'
        },
        '/app/newsletters': {
            'bind': '/mnt/newsletters',
            'mode': 'ro'
        }
    }
    return volumes
