"""
WorkerDeployment model for managing remote worker deployments via SSH
"""
from datetime import datetime
from bson import ObjectId


class WorkerDeployment:
    """Model for worker deployment operations"""

    @staticmethod
    def create(mongo, user_id, deployment_data):
        """
        Create a new worker deployment record

        Args:
            mongo: MongoDB connection
            user_id: User ID who owns the deployment
            deployment_data: Dictionary containing:
                - worker_name: Human-readable name
                - host: Remote server IP/hostname
                - port: SSH port (default 22)
                - username: SSH username
                - ssh_key_name: Reference to SSH key file
                - worker_count: Number of worker containers
                - nsqd_address: NSQ daemon address
                - nsqlookupd_addresses: List of NSQ lookupd addresses
                - mongo_uri: MongoDB connection string
                - server_url: GVPOCR API server URL
                - providers: OCR provider configuration dict

        Returns:
            Created deployment document
        """
        deployment = {
            'user_id': ObjectId(user_id),
            'worker_id': deployment_data.get('worker_id') or f"worker-{ObjectId()}",

            # Connection configuration
            'host': deployment_data['host'],
            'port': deployment_data.get('port', 22),
            'username': deployment_data['username'],
            'ssh_key_name': deployment_data['ssh_key_name'],

            # Docker Socket configuration
            'deployment_type': deployment_data.get('deployment_type', 'ssh'),
            'use_docker_socket': deployment_data.get('use_docker_socket', False),
            'docker_socket_port': deployment_data.get('docker_socket_port', 2375),
            'docker_socket_host': deployment_data.get('docker_socket_host'),
            'docker_tls': deployment_data.get('docker_tls', False),
            'docker_verify_tls': deployment_data.get('docker_verify_tls', False),

            # Worker configuration
            'worker_name': deployment_data['worker_name'],
            'worker_count': deployment_data.get('worker_count', 1),
            'nsqd_address': deployment_data['nsqd_address'],
            'nsqlookupd_addresses': deployment_data['nsqlookupd_addresses'],
            'mongo_uri': deployment_data['mongo_uri'],
            'server_url': deployment_data['server_url'],

            # Provider configuration
            'providers': deployment_data.get('providers', {
                'google_vision_enabled': True,
                'tesseract_enabled': True,
                'ollama_enabled': False,
                'vllm_enabled': False,
                'easyocr_enabled': False,
                'azure_enabled': False
            }),

            # Deployment status
            'status': 'deploying',  # deploying, running, stopped, error, unreachable
            'containers': [],

            # Health tracking
            'last_health_check': None,
            'health_status': 'unknown',  # healthy, degraded, unhealthy, unknown
            'error_message': None,

            # Timestamps
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'deployed_at': None,
            'last_accessed': datetime.utcnow()
        }

        result = mongo.db.worker_deployments.insert_one(deployment)
        deployment['_id'] = result.inserted_id
        return deployment

    @staticmethod
    def find_by_id(mongo, deployment_id, user_id=None):
        """
        Find deployment by ID

        Args:
            mongo: MongoDB connection
            deployment_id: Deployment _id
            user_id: Optional user ID for ownership validation

        Returns:
            Deployment document or None
        """
        query = {'_id': ObjectId(deployment_id)}
        if user_id:
            query['user_id'] = ObjectId(user_id)
        return mongo.db.worker_deployments.find_one(query)

    @staticmethod
    def find_by_worker_id(mongo, worker_id, user_id=None):
        """
        Find deployment by worker_id

        Args:
            mongo: MongoDB connection
            worker_id: Worker identifier
            user_id: Optional user ID for ownership validation

        Returns:
            Deployment document or None
        """
        query = {'worker_id': worker_id}
        if user_id:
            query['user_id'] = ObjectId(user_id)
        return mongo.db.worker_deployments.find_one(query)

    @staticmethod
    def find_by_user(mongo, user_id, skip=0, limit=50):
        """
        Find all deployments for a user

        Args:
            mongo: MongoDB connection
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of deployment documents
        """
        return list(mongo.db.worker_deployments.find(
            {'user_id': ObjectId(user_id)}
        ).sort('created_at', -1).skip(skip).limit(limit))

    @staticmethod
    def find_active_deployments(mongo, user_id=None):
        """
        Find all active deployments (deploying or running status)

        Args:
            mongo: MongoDB connection
            user_id: Optional user ID filter

        Returns:
            List of active deployment documents
        """
        query = {'status': {'$in': ['deploying', 'running']}}
        if user_id:
            query['user_id'] = ObjectId(user_id)
        return list(mongo.db.worker_deployments.find(query).sort('created_at', -1))

    @staticmethod
    def update_status(mongo, deployment_id, status, error_message=None):
        """
        Update deployment status

        Args:
            mongo: MongoDB connection
            deployment_id: Deployment _id
            status: New status value
            error_message: Optional error message

        Returns:
            MongoDB update result
        """
        update_data = {
            'status': status,
            'updated_at': datetime.utcnow()
        }

        if error_message:
            update_data['error_message'] = error_message

        if status == 'running' and not error_message:
            update_data['deployed_at'] = datetime.utcnow()
            update_data['error_message'] = None

        return mongo.db.worker_deployments.update_one(
            {'_id': ObjectId(deployment_id)},
            {'$set': update_data}
        )

    @staticmethod
    def update_containers(mongo, deployment_id, containers):
        """
        Update container information

        Args:
            mongo: MongoDB connection
            deployment_id: Deployment _id
            containers: List of container info dicts

        Returns:
            MongoDB update result
        """
        return mongo.db.worker_deployments.update_one(
            {'_id': ObjectId(deployment_id)},
            {
                '$set': {
                    'containers': containers,
                    'updated_at': datetime.utcnow()
                }
            }
        )

    @staticmethod
    def update_health(mongo, deployment_id, health_data):
        """
        Update health check results

        Args:
            mongo: MongoDB connection
            deployment_id: Deployment _id
            health_data: Dictionary with health information

        Returns:
            MongoDB update result
        """
        update_data = {
            'last_health_check': datetime.utcnow(),
            'health_status': health_data.get('health_status', 'unknown'),
            'updated_at': datetime.utcnow()
        }

        if 'containers' in health_data:
            update_data['containers'] = health_data['containers']

        if 'error_message' in health_data:
            update_data['error_message'] = health_data['error_message']

        return mongo.db.worker_deployments.update_one(
            {'_id': ObjectId(deployment_id)},
            {'$set': update_data}
        )

    @staticmethod
    def update_worker_count(mongo, deployment_id, worker_count):
        """
        Update worker count (for scaling operations)

        Args:
            mongo: MongoDB connection
            deployment_id: Deployment _id
            worker_count: New worker count

        Returns:
            MongoDB update result
        """
        return mongo.db.worker_deployments.update_one(
            {'_id': ObjectId(deployment_id)},
            {
                '$set': {
                    'worker_count': worker_count,
                    'updated_at': datetime.utcnow()
                }
            }
        )

    @staticmethod
    def update_last_accessed(mongo, deployment_id):
        """
        Update last accessed timestamp

        Args:
            mongo: MongoDB connection
            deployment_id: Deployment _id

        Returns:
            MongoDB update result
        """
        return mongo.db.worker_deployments.update_one(
            {'_id': ObjectId(deployment_id)},
            {'$set': {'last_accessed': datetime.utcnow()}}
        )

    @staticmethod
    def delete(mongo, deployment_id, user_id):
        """
        Delete deployment record

        Args:
            mongo: MongoDB connection
            deployment_id: Deployment _id
            user_id: User ID for ownership validation

        Returns:
            MongoDB delete result
        """
        return mongo.db.worker_deployments.delete_one({
            '_id': ObjectId(deployment_id),
            'user_id': ObjectId(user_id)
        })

    @staticmethod
    def update_sshfs_status(mongo, deployment_id, mount_status, mount_errors=None):
        """
        Update SSHFS mount status

        Args:
            mongo: MongoDB connection
            deployment_id: Deployment _id
            mount_status: Mount status (pending, mounted, failed, unmounted)
            mount_errors: List of error messages (optional)

        Returns:
            MongoDB update result
        """
        update_data = {
            'sshfs_config.mount_status': mount_status,
            'sshfs_config.last_mount_check': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        if mount_errors is not None:
            update_data['sshfs_config.mount_errors'] = mount_errors

        return mongo.db.worker_deployments.update_one(
            {'_id': ObjectId(deployment_id)},
            {'$set': update_data}
        )

    @staticmethod
    def to_dict(deployment):
        """
        Convert deployment document to safe dictionary for API responses

        Args:
            deployment: Deployment document from MongoDB

        Returns:
            Dictionary with safe/serializable values
        """
        if not deployment:
            return None

        result = {
            'id': str(deployment['_id']),
            'user_id': str(deployment.get('user_id')),
            'worker_id': deployment.get('worker_id'),

            # Connection config
            'host': deployment.get('host'),
            'port': deployment.get('port'),
            'username': deployment.get('username'),
            'ssh_key_name': deployment.get('ssh_key_name'),

            # Worker config
            'worker_name': deployment.get('worker_name'),
            'worker_count': deployment.get('worker_count'),
            'nsqd_address': deployment.get('nsqd_address'),
            'nsqlookupd_addresses': deployment.get('nsqlookupd_addresses', []),
            'mongo_uri': deployment.get('mongo_uri'),
            'server_url': deployment.get('server_url'),
            'providers': deployment.get('providers', {}),

            # Status
            'status': deployment.get('status'),
            'containers': deployment.get('containers', []),
            'health_status': deployment.get('health_status'),
            'error_message': deployment.get('error_message'),

            # SSHFS config
            'sshfs_config': deployment.get('sshfs_config'),

            # Timestamps
            'created_at': deployment.get('created_at').isoformat() if deployment.get('created_at') else None,
            'updated_at': deployment.get('updated_at').isoformat() if deployment.get('updated_at') else None,
            'deployed_at': deployment.get('deployed_at').isoformat() if deployment.get('deployed_at') else None,
            'last_health_check': deployment.get('last_health_check').isoformat() if deployment.get('last_health_check') else None,
            'last_accessed': deployment.get('last_accessed').isoformat() if deployment.get('last_accessed') else None
        }

        return result
