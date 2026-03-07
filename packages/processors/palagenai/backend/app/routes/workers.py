"""
Routes for worker monitoring and statistics
"""

import logging
import time
import docker
from flask import Blueprint, jsonify, request
from app.services.nsq_service import NSQService
from app.utils.decorators import token_required

logger = logging.getLogger(__name__)

workers_bp = Blueprint('workers', __name__, url_prefix='/api/workers')


def get_container_info_by_hostname(hostname):
    """
    Get Docker container information by hostname

    Returns dict with:
    - container_name: Docker container name (e.g., 'gvpocr-ocr-worker-1')
    - deployment_type: 'swarm', 'compose', or 'unknown'
    - service_name: Swarm service name if applicable
    """
    try:
        client = docker.from_env()
        containers = client.containers.list()

        for container in containers:
            # Check if hostname matches
            container_hostname = container.attrs.get('Config', {}).get('Hostname', '')
            if container_hostname == hostname:
                labels = container.labels

                # Check if it's a swarm service
                if 'com.docker.swarm.service.name' in labels:
                    service_name = labels.get('com.docker.swarm.service.name', '')
                    task_name = labels.get('com.docker.swarm.task.name', '')
                    return {
                        'container_name': task_name if task_name else container.name,
                        'deployment_type': 'swarm',
                        'service_name': service_name,
                        'display_name': f'🐝 {service_name}'
                    }

                # Check if it's from docker-compose
                elif 'com.docker.compose.service' in labels:
                    compose_service = labels.get('com.docker.compose.service', '')
                    project = labels.get('com.docker.compose.project', '')
                    return {
                        'container_name': container.name,
                        'deployment_type': 'compose',
                        'service_name': compose_service,
                        'display_name': f'🐳 {container.name}'
                    }

                # Regular Docker container
                else:
                    return {
                        'container_name': container.name,
                        'deployment_type': 'docker',
                        'service_name': None,
                        'display_name': f'🐋 {container.name}'
                    }

        # Container not found
        return {
            'container_name': hostname,
            'deployment_type': 'unknown',
            'service_name': None,
            'display_name': hostname
        }

    except Exception as e:
        logger.warning(f"Error looking up container for hostname {hostname}: {e}")
        return {
            'container_name': hostname,
            'deployment_type': 'unknown',
            'service_name': None,
            'display_name': hostname
        }


@workers_bp.route('/stats', methods=['GET'])
@token_required
def get_worker_stats(current_user_id):
    """
    Get statistics about connected NSQ workers

    Returns information about:
    - Connected workers and their status
    - Topic statistics (message depth, channels)
    - Worker activity and connection times
    """
    try:
        nsq_service = NSQService()

        # Get stats for the bulk OCR tasks topic
        topic_stats = nsq_service.get_topic_stats('bulk_ocr_file_tasks')

        if not topic_stats:
            return jsonify({
                'success': False,
                'error': 'Unable to retrieve NSQ statistics',
                'workers': [],
                'topic_stats': {}
            }), 503

        # Parse worker information from topic stats
        workers = []
        topic_data = topic_stats.get('topics', [])

        if topic_data:
            # Get the bulk_ocr_file_tasks topic
            for topic in topic_data:
                if topic.get('topic_name') == 'bulk_ocr_file_tasks':
                    channels = topic.get('channels', [])

                    # Look for the bulk_ocr_workers channel
                    for channel in channels:
                        if channel.get('channel_name') == 'bulk_ocr_workers':
                            clients = channel.get('clients', [])

                            for client in clients:
                                # Calculate connected duration from connect_ts
                                connect_ts = client.get('connect_ts', 0)
                                current_ts = int(time.time())
                                duration_seconds = current_ts - connect_ts if connect_ts else 0

                                # Get container information
                                hostname = client.get('hostname', 'unknown')
                                container_info = get_container_info_by_hostname(hostname)

                                worker_info = {
                                    'client_id': client.get('client_id', 'unknown'),
                                    'hostname': hostname,
                                    'container_name': container_info['container_name'],
                                    'deployment_type': container_info['deployment_type'],
                                    'service_name': container_info['service_name'],
                                    'display_name': container_info['display_name'],
                                    'remote_address': client.get('remote_address', 'unknown'),
                                    'state': client.get('state', 0),  # 0=init, 1=disconnected, 2=connected, 3=subscribing, 4=ready
                                    'ready_count': client.get('ready_count', 0),
                                    'in_flight_count': client.get('in_flight_count', 0),
                                    'message_count': client.get('message_count', 0),
                                    'finish_count': client.get('finish_count', 0),
                                    'requeue_count': client.get('requeue_count', 0),
                                    'connected_duration': duration_seconds * 1_000_000_000,  # Convert to nanoseconds
                                    'user_agent': client.get('user_agent', 'unknown'),
                                    'version': client.get('version', 'unknown')
                                }

                                # Determine worker status
                                state_val = worker_info['state']
                                if state_val == 4:
                                    worker_info['status'] = 'ready'
                                elif state_val == 3:
                                    worker_info['status'] = 'subscribing'
                                elif state_val == 2:
                                    worker_info['status'] = 'connected'
                                elif state_val == 1:
                                    worker_info['status'] = 'disconnected'
                                else:
                                    worker_info['status'] = 'initializing'

                                # Check if worker is actively processing
                                if worker_info['in_flight_count'] > 0:
                                    worker_info['activity'] = 'processing'
                                elif worker_info['ready_count'] > 0:
                                    worker_info['activity'] = 'idle'
                                else:
                                    worker_info['activity'] = 'waiting'

                                workers.append(worker_info)

                            # Get channel-level statistics
                            channel_stats = {
                                'depth': channel.get('depth', 0),  # Messages waiting
                                'in_flight_count': channel.get('in_flight_count', 0),  # Messages being processed
                                'deferred_count': channel.get('deferred_count', 0),
                                'requeue_count': channel.get('requeue_count', 0),
                                'timeout_count': channel.get('timeout_count', 0),
                                'message_count': channel.get('message_count', 0),
                                'client_count': len(clients)
                            }

        # Get overall topic statistics
        topic_summary = {}
        if topic_data:
            for topic in topic_data:
                if topic.get('topic_name') == 'bulk_ocr_file_tasks':
                    topic_summary = {
                        'depth': topic.get('depth', 0),
                        'message_count': topic.get('message_count', 0),
                        'channel_count': len(topic.get('channels', []))
                    }

        return jsonify({
            'success': True,
            'workers': workers,
            'worker_count': len(workers),
            'channel_stats': channel_stats if 'channel_stats' in locals() else {},
            'topic_stats': topic_summary,
            'nsq_address': nsq_service.nsqd_address
        }), 200

    except Exception as e:
        logger.error(f"Error fetching worker stats: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'workers': [],
            'worker_count': 0
        }), 500
