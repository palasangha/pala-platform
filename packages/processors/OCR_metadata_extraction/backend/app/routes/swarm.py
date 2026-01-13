"""
Docker Swarm API Routes

Provides REST API endpoints for managing Docker Swarm and OCR workers
"""

from flask import Blueprint, request, jsonify
from functools import wraps
import logging

from app.services.swarm_service import get_swarm_service

logger = logging.getLogger(__name__)

swarm_bp = Blueprint('swarm', __name__, url_prefix='/api/swarm')


def handle_errors(f):
    """Decorator to handle errors consistently"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    return decorated_function


# ==================== Swarm Information ====================

@swarm_bp.route('/info', methods=['GET'])
@handle_errors
def get_swarm_info():
    """Get swarm cluster information"""
    swarm_service = get_swarm_service()
    success, swarm_info, error = swarm_service.get_swarm_info()
    
    if not success:
        return jsonify({'success': False, 'error': error}), 400
    
    return jsonify({
        'success': True,
        'data': swarm_info.to_dict() if swarm_info else None
    })


@swarm_bp.route('/init', methods=['POST'])
@handle_errors
def init_swarm():
    """Initialize Docker Swarm"""
    data = request.get_json()
    advertise_addr = data.get('advertise_addr', '127.0.0.1')
    
    swarm_service = get_swarm_service()
    success, message = swarm_service.init_swarm(advertise_addr)
    
    if not success:
        return jsonify({'success': False, 'error': message}), 400
    
    return jsonify({'success': True, 'message': message})


@swarm_bp.route('/leave', methods=['POST'])
@handle_errors
def leave_swarm():
    """Leave Docker Swarm"""
    data = request.get_json() or {}
    force = data.get('force', False)
    
    swarm_service = get_swarm_service()
    success, message = swarm_service.leave_swarm(force=force)
    
    if not success:
        return jsonify({'success': False, 'error': message}), 400
    
    return jsonify({'success': True, 'message': message})


@swarm_bp.route('/join-token/<role>', methods=['GET'])
@handle_errors
def get_join_token(role):
    """Get swarm join token for workers or managers"""
    if role not in ['worker', 'manager']:
        return jsonify({'success': False, 'error': 'Invalid role'}), 400
    
    swarm_service = get_swarm_service()
    success, token, error = swarm_service.get_join_token(role=role)
    
    if not success:
        return jsonify({'success': False, 'error': error}), 400
    
    return jsonify({
        'success': True,
        'token': token,
        'role': role,
        'manager_ip': '172.12.0.132',
        'manager_port': 2377
    })


# ==================== Node Management ====================

@swarm_bp.route('/nodes', methods=['GET'])
@handle_errors
def list_nodes():
    """List all swarm nodes"""
    swarm_service = get_swarm_service()
    success, nodes, error = swarm_service.list_nodes()
    
    if not success:
        return jsonify({'success': False, 'error': error}), 400
    
    return jsonify({
        'success': True,
        'count': len(nodes),
        'data': [n.to_dict() for n in nodes]
    })


@swarm_bp.route('/nodes/<node_id>', methods=['GET'])
@handle_errors
def inspect_node(node_id):
    """Get detailed information about a node"""
    swarm_service = get_swarm_service()
    success, node_info, error = swarm_service.inspect_node(node_id)
    
    if not success:
        return jsonify({'success': False, 'error': error}), 400
    
    return jsonify({
        'success': True,
        'data': node_info
    })


@swarm_bp.route('/nodes/<node_id>/drain', methods=['POST'])
@handle_errors
def drain_node(node_id):
    """Drain a node - prevent new tasks from being scheduled"""
    swarm_service = get_swarm_service()
    success, message = swarm_service.update_node_availability(node_id, 'drain')
    
    if not success:
        return jsonify({'success': False, 'error': message}), 400
    
    return jsonify({'success': True, 'message': message})


@swarm_bp.route('/nodes/<node_id>/promote', methods=['POST'])
@handle_errors
def promote_node(node_id):
    """Promote a worker node to manager"""
    swarm_service = get_swarm_service()
    success, message = swarm_service.promote_node(node_id)
    
    if not success:
        return jsonify({'success': False, 'error': message}), 400
    
    return jsonify({'success': True, 'message': message})


@swarm_bp.route('/nodes/<node_id>/demote', methods=['POST'])
@handle_errors
def demote_node(node_id):
    """Demote a manager node to worker"""
    swarm_service = get_swarm_service()
    success, message = swarm_service.demote_node(node_id)
    
    if not success:
        return jsonify({'success': False, 'error': message}), 400
    
    return jsonify({'success': True, 'message': message})


@swarm_bp.route('/nodes/<node_id>', methods=['DELETE'])
@handle_errors
def remove_node(node_id):
    """Remove a node from swarm"""
    data = request.get_json() or {}
    force = data.get('force', False)
    
    swarm_service = get_swarm_service()
    success, message = swarm_service.remove_node(node_id, force=force)
    
    if not success:
        return jsonify({'success': False, 'error': message}), 400
    
    return jsonify({'success': True, 'message': message})


# ==================== Service Management ====================

@swarm_bp.route('/services', methods=['GET'])
@handle_errors
def list_services():
    """List all swarm services"""
    logger.info("[ROUTE] GET /api/swarm/services called")
    swarm_service = get_swarm_service()
    success, services, error = swarm_service.list_services()
    
    logger.info(f"[ROUTE] Services list result - success: {success}, count: {len(services) if success else 0}")
    
    if not success:
        logger.error(f"[ROUTE] Failed to list services: {error}")
        return jsonify({'success': False, 'error': error}), 400
    
    response_data = [s.to_dict() for s in services]
    logger.info(f"[ROUTE] Returning {len(response_data)} services: {response_data}")
    
    return jsonify({
        'success': True,
        'count': len(services),
        'data': response_data
    })


@swarm_bp.route('/services', methods=['POST'])
@handle_errors
def create_service():
    """Create a new service"""
    data = request.get_json()
    logger.info(f"[ROUTE] POST /api/swarm/services - data: {data}")

    name = data.get('name')
    image = data.get('image')
    replicas = data.get('replicas', 1)
    mongo_uri = data.get('mongo_uri')
    env_vars = data.get('env_vars', {})

    logger.info(f"[ROUTE] Creating service - name: {name}, image: {image}, replicas: {replicas}")

    if not name or not image:
        logger.error("[ROUTE] Missing required fields: name or image")
        return jsonify({'success': False, 'error': 'name and image required'}), 400

    swarm_service = get_swarm_service()
    success, message = swarm_service.create_service(name, image, replicas, mongo_uri, env_vars)

    logger.info(f"[ROUTE] Service creation result - success: {success}, message: {message}")

    if not success:
        logger.error(f"[ROUTE] Failed to create service: {message}")
        return jsonify({'success': False, 'error': message}), 400

    return jsonify({'success': True, 'message': message})


@swarm_bp.route('/services/<service_name>/scale', methods=['POST'])
@handle_errors
def scale_service(service_name):
    """Scale a service to desired number of replicas"""
    data = request.get_json()
    replicas = data.get('replicas')
    
    if replicas is None or not isinstance(replicas, int):
        return jsonify({'success': False, 'error': 'replicas (int) required'}), 400
    
    swarm_service = get_swarm_service()
    success, message = swarm_service.scale_service(service_name, replicas)
    
    if not success:
        return jsonify({'success': False, 'error': message}), 400
    
    return jsonify({'success': True, 'message': message, 'replicas': replicas})


@swarm_bp.route('/services/<service_name>/image', methods=['PUT'])
@handle_errors
def update_service_image(service_name):
    """Update service image"""
    data = request.get_json()
    image = data.get('image')
    
    if not image:
        return jsonify({'success': False, 'error': 'image required'}), 400
    
    swarm_service = get_swarm_service()
    success, message = swarm_service.update_service_image(service_name, image)
    
    if not success:
        return jsonify({'success': False, 'error': message}), 400
    
    return jsonify({'success': True, 'message': message})


@swarm_bp.route('/services/<service_name>', methods=['DELETE'])
@handle_errors
def remove_service(service_name):
    """Remove a service from swarm"""
    swarm_service = get_swarm_service()
    success, message = swarm_service.remove_service(service_name)
    
    if not success:
        return jsonify({'success': False, 'error': message}), 400
    
    return jsonify({'success': True, 'message': message})


# ==================== Task Management ====================

@swarm_bp.route('/tasks', methods=['GET'])
@handle_errors
def list_all_tasks():
    """List all swarm tasks"""
    swarm_service = get_swarm_service()
    success, tasks, error = swarm_service.list_all_tasks()
    
    if not success:
        return jsonify({'success': False, 'error': error}), 400
    
    return jsonify({
        'success': True,
        'count': len(tasks),
        'data': [t.to_dict() for t in tasks]
    })


@swarm_bp.route('/services/<service_name>/tasks', methods=['GET'])
@handle_errors
def list_service_tasks(service_name):
    """List all tasks for a service"""
    swarm_service = get_swarm_service()
    success, tasks, error = swarm_service.list_service_tasks(service_name)
    
    if not success:
        return jsonify({'success': False, 'error': error}), 400
    
    return jsonify({
        'success': True,
        'service': service_name,
        'count': len(tasks),
        'data': [t.to_dict() for t in tasks]
    })


@swarm_bp.route('/services/<service_name>/logs', methods=['GET'])
@handle_errors
def get_service_logs(service_name):
    """Get logs from service tasks"""
    tail = request.args.get('tail', 100, type=int)
    
    swarm_service = get_swarm_service()
    success, logs, error = swarm_service.get_service_logs(service_name, tail=tail)
    
    if not success:
        return jsonify({'success': False, 'error': error}), 400
    
    return jsonify({
        'success': True,
        'service': service_name,
        'tail': tail,
        'logs': logs
    })


# ==================== Health & Diagnostics ====================

@swarm_bp.route('/health', methods=['GET'])
@handle_errors
def get_health_status():
    """Get comprehensive health status of swarm"""
    swarm_service = get_swarm_service()
    success, health_status, error = swarm_service.get_health_status()
    
    if not success:
        return jsonify({'success': False, 'error': error}), 400
    
    return jsonify({
        'success': True,
        'data': health_status
    })


@swarm_bp.route('/statistics', methods=['GET'])
@handle_errors
def get_statistics():
    """Get comprehensive statistics about swarm"""
    swarm_service = get_swarm_service()
    success, statistics, error = swarm_service.get_statistics()
    
    if not success:
        return jsonify({'success': False, 'error': error}), 400
    
    return jsonify({
        'success': True,
        'data': statistics
    })


# ==================== Stack Management ====================

@swarm_bp.route('/deploy-stack', methods=['POST'])
@handle_errors
def deploy_stack():
    """Deploy a stack from compose file"""
    data = request.get_json()
    stack_file = data.get('stack_file')
    stack_name = data.get('stack_name')
    
    if not stack_file or not stack_name:
        return jsonify({'success': False, 'error': 'stack_file and stack_name required'}), 400
    
    swarm_service = get_swarm_service()
    success, message = swarm_service.deploy_stack(stack_file, stack_name)
    
    if not success:
        return jsonify({'success': False, 'error': message}), 400
    
    return jsonify({'success': True, 'message': message})


# ==================== Remote Worker Management ====================

@swarm_bp.route('/join-node', methods=['POST'])
@handle_errors
def join_node_to_swarm():
    """Join a remote machine to the Swarm cluster"""
    data = request.get_json()
    
    host = data.get('host')
    username = data.get('username')
    ssh_key = data.get('ssh_key')
    ssh_key_path = data.get('ssh_key_path')
    
    if not host or not username:
        return jsonify({
            'success': False,
            'error': 'host and username are required'
        }), 400
    
    swarm_service = get_swarm_service()
    success, message, error = swarm_service.join_node_to_swarm(
        host=host,
        username=username,
        ssh_key=ssh_key,
        ssh_key_path=ssh_key_path
    )
    
    if not success:
        return jsonify({
            'success': False,
            'error': error,
            'message': message
        }), 400
    
    return jsonify({
        'success': True,
        'message': message,
        'host': host
    })


@swarm_bp.route('/launch-remote-worker', methods=['POST'])
@handle_errors
def launch_remote_worker():
    """Launch Docker worker on a remote machine via SSH"""
    data = request.get_json()
    
    host = data.get('host')
    username = data.get('username')
    password = data.get('password')
    docker_image = data.get('docker_image', 'registry.docgenai.com:5010/gvpocr-worker-updated:latest')
    worker_name = data.get('worker_name', f'worker-{host}')
    replica_count = data.get('replica_count', 1)
    
    if not host or not username or not password:
        return jsonify({
            'success': False,
            'error': 'host, username, and password are required'
        }), 400
    
    swarm_service = get_swarm_service()
    success, result, error = swarm_service.launch_remote_worker(
        host=host,
        username=username,
        password=password,
        docker_image=docker_image,
        worker_name=worker_name,
        replica_count=replica_count
    )
    
    if not success:
        return jsonify({
            'success': False,
            'error': error,
            'result': result
        }), 400
    
    return jsonify({
        'success': True,
        'message': f'Worker launched on {host}',
        'data': result
    })


def register_swarm_routes(app):
    """Register swarm routes with Flask app"""
    app.register_blueprint(swarm_bp)
    logger.info("Swarm routes registered")
