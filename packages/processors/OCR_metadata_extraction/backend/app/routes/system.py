"""
System management routes - service configuration, URLs, and restart functionality
"""

import os
import logging
import subprocess
from flask import Blueprint, jsonify, request
from app.utils.decorators import token_required

logger = logging.getLogger(__name__)

system_bp = Blueprint('system', __name__, url_prefix='/api/system')


@system_bp.route('/status', methods=['GET'])
@token_required
def get_system_status(current_user_id):
    """Get current system and service status"""
    try:
        status = {
            'backend': get_backend_status(),
            'frontend': get_frontend_status(),
            'running_services': get_docker_services_status(),
            'configured_services': get_docker_compose_services(),
            'environment': get_environment_info(),
        }
        return jsonify({
            'success': True,
            'status': status
        }), 200
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500


def get_backend_status():
    """Get backend service status"""
    return {
        'name': 'Backend API',
        'url': os.getenv('BACKEND_URL', 'http://localhost:5000'),
        'version': os.getenv('BACKEND_VERSION', 'Unknown'),
        'debug': os.getenv('FLASK_ENV') == 'development',
        'port': os.getenv('FLASK_PORT', '5000'),
        'host': os.getenv('FLASK_HOST', 'localhost'),
    }


def get_frontend_status():
    """Get frontend service status"""
    return {
        'name': 'Frontend Web',
        'url': os.getenv('FRONTEND_URL', 'http://localhost:3000'),
        'version': os.getenv('FRONTEND_VERSION', 'Unknown'),
        'environment': os.getenv('NODE_ENV', 'development'),
        'port': os.getenv('FRONTEND_PORT', '3000'),
    }


def get_docker_services_status():
    """Get status of Docker services from docker-compose"""
    try:
        # First try docker ps to get running containers
        result = subprocess.run(
            ['docker', 'ps', '--format', '{{json .}}'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            logger.warning(f"Docker ps failed: {result.stderr}")
            return []
        
        import json
        services = []
        
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                try:
                    container = json.loads(line)
                    
                    # Extract service name from Names (could have multiple names separated by comma)
                    names = container.get('Names', 'unknown')
                    if isinstance(names, str) and names:
                        service_name = names.split(',')[0]  # Get first name if multiple
                    else:
                        service_name = 'unknown'
                    
                    # Parse status to extract health and uptime
                    status = container.get('Status', 'unknown')
                    
                    # Extract port mappings
                    ports = container.get('Ports', '')
                    
                    services.append({
                        'name': service_name,
                        'status': status,
                        'image': container.get('Image', 'unknown'),
                        'container_id': container.get('ID', 'unknown')[:12],
                        'ports': ports,
                        'image_id': container.get('ImageID', 'unknown')[:12],
                        'state': container.get('State', 'unknown'),
                    })
                except json.JSONDecodeError as e:
                    logger.debug(f"Failed to parse container JSON: {e}")
                    continue
        
        # Sort by service name for consistent ordering
        services.sort(key=lambda x: x['name'])
        
        logger.info(f"Found {len(services)} running Docker services")
        return services
        
    except FileNotFoundError:
        logger.warning("Docker command not found")
        return []
    except Exception as e:
        logger.warning(f"Error getting Docker services: {str(e)}")
        return []


def get_docker_compose_services():
    """Get list of services from docker-compose.yml"""
    try:
        import yaml
        
        # Find docker-compose.yml file
        current_dir = os.getcwd()
        docker_compose_path = os.path.join(current_dir, 'docker-compose.yml')
        
        if not os.path.exists(docker_compose_path):
            docker_compose_path = os.path.join(current_dir, '..', 'docker-compose.yml')
        
        if not os.path.exists(docker_compose_path):
            logger.warning("docker-compose.yml not found")
            return {}
        
        with open(docker_compose_path, 'r') as f:
            compose_data = yaml.safe_load(f)
        
        services = compose_data.get('services', {})
        
        service_list = {}
        for service_name, service_config in services.items():
            service_list[service_name] = {
                'name': service_name,
                'image': service_config.get('image', 'N/A'),
                'ports': service_config.get('ports', []),
                'environment': bool(service_config.get('environment')),
                'volumes': bool(service_config.get('volumes')),
                'depends_on': service_config.get('depends_on', []),
            }
        
        logger.info(f"Found {len(service_list)} services in docker-compose.yml")
        return service_list
        
    except ImportError:
        logger.warning("PyYAML not installed, cannot parse docker-compose.yml")
        return {}
    except Exception as e:
        logger.warning(f"Error parsing docker-compose.yml: {str(e)}")
        return {}


def get_environment_info():
    """Get environment and configuration info"""
    return {
        'archipelago_enabled': os.getenv('ARCHIPELAGO_ENABLED', 'false') == 'true',
        'archipelago_url': os.getenv('ARCHIPELAGO_BASE_URL', 'Not configured'),
        'archipelago_verify_ssl': os.getenv('ARCHIPELAGO_VERIFY_SSL', 'true') == 'true',
        'mongodb_enabled': bool(os.getenv('MONGO_URI')),
        'nsq_enabled': bool(os.getenv('NSQD_ADDRESS')),
        'swarm_enabled': os.getenv('SWARM_MODE', 'false') == 'true',
        'debug_mode': os.getenv('DEBUG', 'false') == 'true',
    }


@system_bp.route('/config', methods=['GET'])
@token_required
def get_system_config(current_user_id):
    """Get system configuration"""
    try:
        config = {
            'backend': {
                'url': os.getenv('BACKEND_URL', 'http://localhost:5000'),
                'port': os.getenv('FLASK_PORT', '5000'),
                'host': os.getenv('FLASK_HOST', 'localhost'),
                'environment': os.getenv('FLASK_ENV', 'development'),
                'workers': os.getenv('GUNICORN_WORKERS', '4'),
            },
            'frontend': {
                'url': os.getenv('FRONTEND_URL', 'http://localhost:3000'),
                'port': os.getenv('FRONTEND_PORT', '3000'),
                'environment': os.getenv('NODE_ENV', 'development'),
            },
            'archipelago': {
                'enabled': os.getenv('ARCHIPELAGO_ENABLED', 'false') == 'true',
                'base_url': os.getenv('ARCHIPELAGO_BASE_URL', ''),
                'username': bool(os.getenv('ARCHIPELAGO_USERNAME')),  # Don't expose actual username
                'verify_ssl': os.getenv('ARCHIPELAGO_VERIFY_SSL', 'true') == 'true',
            },
            'database': {
                'mongodb_connected': bool(os.getenv('MONGO_URI')),
                'mongo_db': os.getenv('MONGO_DB', 'gvpocr'),
            },
            'queue': {
                'nsq_enabled': bool(os.getenv('NSQD_ADDRESS')),
                'nsqd_address': os.getenv('NSQD_ADDRESS', 'Not configured'),
                'nsqlookupd': os.getenv('NSQLOOKUPD_ADDRESSES', 'Not configured'),
            },
            'docker': {
                'swarm_mode': os.getenv('SWARM_MODE', 'false') == 'true',
                'worker_image': os.getenv('WORKER_IMAGE', 'gvpocr-worker:latest'),
            },
        }
        
        return jsonify({
            'success': True,
            'config': config
        }), 200
    except Exception as e:
        logger.error(f"Error getting system config: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500


@system_bp.route('/restart', methods=['POST'])
@token_required
def restart_service(current_user_id):
    """Restart a service (requires admin)"""
    # TODO: Add admin check here
    
    data = request.get_json()
    service_name = data.get('service')
    
    if not service_name:
        return jsonify({'error': 'Service name required'}), 400
    
    try:
        logger.warning(f"Restarting service: {service_name}")
        
        result = subprocess.run(
            ['docker-compose', 'restart', service_name],
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.error(f"Restart failed: {result.stderr}")
            return jsonify({
                'success': False,
                'error': f'Failed to restart {service_name}: {result.stderr}'
            }), 500
        
        return jsonify({
            'success': True,
            'message': f'{service_name} restarted successfully',
            'output': result.stdout
        }), 200
        
    except Exception as e:
        logger.error(f"Error restarting service: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500


@system_bp.route('/env-update', methods=['POST'])
@token_required
def update_environment(current_user_id):
    """Update environment variables (requires admin)"""
    # TODO: Add admin check here
    
    data = request.get_json()
    updates = data.get('updates', {})
    
    if not updates:
        return jsonify({'error': 'No updates provided'}), 400
    
    try:
        # Load current .env file
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..', '.env')
        
        if not os.path.exists(env_file):
            return jsonify({'error': '.env file not found'}), 404
        
        # Read current env
        current_env = {}
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    current_env[key] = value
        
        # Update with new values (only allow safe keys)
        allowed_keys = {
            'ARCHIPELAGO_BASE_URL',
            'ARCHIPELAGO_VERIFY_SSL',
            'FLASK_PORT',
            'FLASK_HOST',
            'FRONTEND_PORT',
            'SWARM_MODE',
            'DEBUG',
        }
        
        updated_keys = set()
        for key, value in updates.items():
            if key in allowed_keys:
                current_env[key] = str(value)
                updated_keys.add(key)
            else:
                logger.warning(f"Attempted to update restricted key: {key}")
        
        # Write back to file
        with open(env_file, 'w') as f:
            for key, value in current_env.items():
                f.write(f"{key}={value}\n")
        
        logger.info(f"Updated environment variables: {updated_keys}")
        
        return jsonify({
            'success': True,
            'message': f'Updated {len(updated_keys)} environment variables',
            'updated_keys': list(updated_keys)
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating environment: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500


@system_bp.route('/docker-logs/<service_name>', methods=['GET'])
@token_required
def get_docker_logs(current_user_id, service_name):
    """Get Docker service logs"""
    try:
        lines = request.args.get('lines', '50', type=int)

        result = subprocess.run(
            ['docker', 'logs', '--tail', str(lines), service_name],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return jsonify({
                'error': f'Failed to get logs for {service_name}',
                'details': result.stderr
            }), 500

        return jsonify({
            'success': True,
            'service': service_name,
            'lines': lines,
            'logs': result.stdout
        }), 200

    except Exception as e:
        logger.error(f"Error getting docker logs: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500


@system_bp.route('/env-variables', methods=['GET'])
def get_env_variables():
    """Get environment variables from docker-compose.yml"""
    try:
        import yaml
        import re

        # Find docker-compose.yml file - search in multiple locations
        current_dir = os.getcwd()
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # app/routes/system.py -> backend dir

        # Primary locations to search
        possible_locations = [
            '/app/docker-compose.yml',  # Docker mounted path (primary)
            os.path.join(current_dir, 'docker-compose.yml'),  # Current directory
            os.path.join(current_dir, '..', 'docker-compose.yml'),  # Parent directory
            '/mnt/sda1/mango1_home/gvpocr/docker-compose.yml',  # Host path (fallback)
            os.path.join(backend_dir, '..', 'docker-compose.yml'),  # Relative from backend
            '/root/docker-compose.yml'
        ]

        docker_compose_file = None
        for location in possible_locations:
            try:
                if os.path.exists(location):
                    docker_compose_file = location
                    logger.info(f"Found docker-compose.yml at: {location}")
                    break
            except Exception as e:
                logger.debug(f"Error checking {location}: {e}")
                continue

        if not docker_compose_file:
            logger.warning(f"docker-compose.yml not found. Searched: {possible_locations}, cwd: {current_dir}, backend_dir: {backend_dir}")
            return jsonify({
                'success': False,
                'error': 'docker-compose.yml file not found',
                'searched_locations': possible_locations,
                'current_dir': current_dir,
                'backend_dir': backend_dir
            }), 404

        # Read and parse docker-compose.yml
        with open(docker_compose_file, 'r') as f:
            compose_data = yaml.safe_load(f)

        # Extract environment variables from all services
        env_variables = {}

        if 'services' in compose_data:
            for service_name, service_config in compose_data['services'].items():
                if isinstance(service_config, dict) and 'environment' in service_config:
                    env_list = service_config['environment']

                    if isinstance(env_list, dict):
                        # Environment as dictionary
                        for key, value in env_list.items():
                            if key not in env_variables:
                                env_variables[key] = {
                                    'value': str(value) if value is not None else '',
                                    'services': [service_name]
                                }
                            else:
                                if service_name not in env_variables[key]['services']:
                                    env_variables[key]['services'].append(service_name)
                    elif isinstance(env_list, list):
                        # Environment as list of strings
                        for env_item in env_list:
                            if isinstance(env_item, str) and '=' in env_item:
                                key, value = env_item.split('=', 1)
                                key = key.strip()
                                value = value.strip()

                                if key not in env_variables:
                                    env_variables[key] = {
                                        'value': value,
                                        'services': [service_name]
                                    }
                                else:
                                    if service_name not in env_variables[key]['services']:
                                        env_variables[key]['services'].append(service_name)

        # Format response
        formatted_variables = {}
        for key, data in env_variables.items():
            formatted_variables[key] = {
                'value': data['value'],
                'services': data['services'],
                'service_count': len(data['services'])
            }

        logger.info(f"Retrieved {len(formatted_variables)} unique environment variables from {len(compose_data.get('services', {}))} services")

        return jsonify({
            'success': True,
            'variables': formatted_variables,
            'count': len(formatted_variables),
            'services_count': len(compose_data.get('services', {}))
        }), 200

    except ImportError:
        logger.warning("PyYAML not installed")
        return jsonify({
            'success': False,
            'error': 'PyYAML library not available'
        }), 500
    except Exception as e:
        logger.error(f"Error getting environment variables: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500
