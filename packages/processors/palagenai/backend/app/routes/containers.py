"""
Routes for Docker container and service management
"""

import logging
import yaml
import os
from flask import Blueprint, jsonify, request
from app.utils.decorators import token_required

logger = logging.getLogger(__name__)

containers_bp = Blueprint('containers', __name__, url_prefix='/api/containers')

def load_compose_config():
    """Load docker-compose.yml configuration"""
    try:
        compose_path = '/mnt/sda1/mango1_home/gvpocr/docker-compose.yml'
        if not os.path.exists(compose_path):
            logger.error(f'[CONTAINERS] docker-compose.yml not found at {compose_path}')
            return {}
        
        with open(compose_path, 'r') as f:
            config = yaml.safe_load(f)
            logger.info(f'[CONTAINERS] Loaded compose config with {len(config.get("services", {}))} services')
            return config.get('services', {})
    except Exception as e:
        logger.error(f'[CONTAINERS] Error loading compose config: {e}', exc_info=True)
        return {}


@containers_bp.route('', methods=['GET', 'OPTIONS'])
@token_required
def get_containers(current_user):
    """Get all services from docker-compose.yml with basic container info"""
    if request.method == 'OPTIONS':
        return '', 204
    
    logger.info(f'[CONTAINERS] Request received from user: {current_user}')
    
    try:
        services = load_compose_config()
        containers_list = []
        
        for service_name, service_config in services.items():
            try:
                container_info = {
                    'name': service_name,
                    'image': service_config.get('image', 'N/A'),
                    'container_name': service_config.get('container_name', service_name),
                    'status': 'unknown',
                    'ports': service_config.get('ports', []),
                    'environment': list(service_config.get('environment', {}).keys()) if isinstance(service_config.get('environment'), dict) else [],
                    'restart_policy': service_config.get('restart', 'no'),
                    'volumes': service_config.get('volumes', []),
                    'networks': service_config.get('networks', []),
                    'depends_on': service_config.get('depends_on', []),
                }
                containers_list.append(container_info)
                logger.info(f'[CONTAINERS] Loaded service config: {service_name}')
            except Exception as e:
                logger.error(f'[CONTAINERS] Error processing service {service_name}: {e}', exc_info=True)
        
        logger.info(f'[CONTAINERS] Returning {len(containers_list)} services')
        return jsonify({'containers': containers_list, 'total': len(containers_list)}), 200
    except Exception as e:
        logger.error(f'[CONTAINERS] Fatal error: {e}', exc_info=True)
        return jsonify({'error': str(e), 'containers': []}), 500
