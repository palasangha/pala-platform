"""
SupervisorHealthChecker - Background service for periodic health monitoring

Periodically checks health of all active worker deployments and implements
auto-restart logic for failed workers.
"""
import threading
import time
import logging
from datetime import datetime
from app.services.supervisor_service import SupervisorService
from app.models.worker_deployment import WorkerDeployment
from app.models import mongo


logger = logging.getLogger(__name__)


class SupervisorHealthChecker:
    """Background service to periodically check worker health"""

    def __init__(self, check_interval=60):
        """
        Initialize health checker

        Args:
            check_interval: Seconds between health checks (default 60)
        """
        self.check_interval = check_interval
        self.running = False
        self.thread = None
        self.supervisor = SupervisorService()
        self.logger = logging.getLogger(__name__)

    def start(self):
        """Start background health checking thread"""
        if self.running:
            self.logger.warning("Health checker is already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._check_loop, daemon=True)
        self.thread.start()
        self.logger.info(f"Health checker started (interval: {self.check_interval}s)")

    def stop(self):
        """Stop background health checking"""
        if not self.running:
            return

        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.logger.info("Health checker stopped")

    def _check_loop(self):
        """Main health checking loop"""
        while self.running:
            try:
                self._check_all_deployments()
            except Exception as e:
                self.logger.error(f"Error in health check loop: {str(e)}", exc_info=True)

            # Sleep for check_interval seconds
            time.sleep(self.check_interval)

    def _check_all_deployments(self):
        """Check health of all active deployments"""
        try:
            # Get all active deployments (deploying or running)
            deployments = WorkerDeployment.find_active_deployments(mongo)

            if not deployments:
                self.logger.debug("No active deployments to check")
                return

            self.logger.info(f"Checking health of {len(deployments)} deployment(s)")

            for deployment in deployments:
                try:
                    self._check_deployment_health(deployment)
                except Exception as e:
                    self.logger.error(
                        f"Error checking deployment {deployment.get('worker_id')}: {str(e)}",
                        exc_info=True
                    )

        except Exception as e:
            self.logger.error(f"Error fetching active deployments: {str(e)}", exc_info=True)

    def _check_deployment_health(self, deployment):
        """
        Check health of a single deployment

        Args:
            deployment: Deployment document from MongoDB
        """
        deployment_id = str(deployment['_id'])
        worker_id = deployment.get('worker_id', 'unknown')

        self.logger.debug(f"Checking health of deployment {worker_id}")

        try:
            # Perform health check
            health_data = self.supervisor.check_worker_health(deployment)

            # Update health in database
            WorkerDeployment.update_health(mongo, deployment_id, health_data)

            current_status = deployment.get('status')
            health_status = health_data.get('health_status')

            # Update deployment status based on health
            if health_status == 'healthy':
                if current_status != 'running':
                    WorkerDeployment.update_status(mongo, deployment_id, 'running')
                    self.logger.info(f"Deployment {worker_id} is now healthy")

            elif health_status == 'degraded':
                if current_status != 'running':
                    WorkerDeployment.update_status(mongo, deployment_id, 'running')
                self.logger.warning(
                    f"Deployment {worker_id} is degraded: "
                    f"{health_data.get('running_containers', 0)}/{health_data.get('total_containers', 0)} containers running"
                )

                # Auto-restart degraded workers
                self._auto_restart_deployment(deployment)

            elif health_status == 'unhealthy':
                WorkerDeployment.update_status(
                    mongo,
                    deployment_id,
                    'error',
                    error_message='All containers are unhealthy'
                )
                self.logger.error(f"Deployment {worker_id} is unhealthy")

                # Auto-restart unhealthy workers
                self._auto_restart_deployment(deployment)

            elif health_status == 'unreachable':
                WorkerDeployment.update_status(
                    mongo,
                    deployment_id,
                    'unreachable',
                    error_message=health_data.get('error_message', 'SSH connection failed')
                )
                self.logger.error(
                    f"Deployment {worker_id} is unreachable: {health_data.get('error_message')}"
                )

        except Exception as e:
            self.logger.error(f"Health check failed for {worker_id}: {str(e)}", exc_info=True)
            WorkerDeployment.update_status(
                mongo,
                deployment_id,
                'error',
                error_message=str(e)
            )

    def _auto_restart_deployment(self, deployment):
        """
        Auto-restart a deployment if configured and needed

        Args:
            deployment: Deployment document from MongoDB
        """
        worker_id = deployment.get('worker_id', 'unknown')
        deployment_id = str(deployment['_id'])

        # Check if last restart was recent (avoid restart loops)
        last_health_check = deployment.get('last_health_check')
        if last_health_check:
            # Only restart if last check was more than 5 minutes ago
            time_since_check = (datetime.utcnow() - last_health_check).total_seconds()
            if time_since_check < 300:  # 5 minutes
                self.logger.debug(f"Skipping auto-restart for {worker_id} (too recent)")
                return

        try:
            self.logger.info(f"Auto-restarting deployment {worker_id}")

            # Attempt restart
            success = self.supervisor.restart_workers(deployment)

            if success:
                WorkerDeployment.update_status(mongo, deployment_id, 'running')
                self.logger.info(f"Successfully auto-restarted deployment {worker_id}")
            else:
                self.logger.error(f"Failed to auto-restart deployment {worker_id}")

        except Exception as e:
            self.logger.error(f"Error auto-restarting deployment {worker_id}: {str(e)}", exc_info=True)


# Global instance
_health_checker_instance = None


def get_health_checker(check_interval=60):
    """
    Get or create global health checker instance

    Args:
        check_interval: Seconds between health checks

    Returns:
        SupervisorHealthChecker instance
    """
    global _health_checker_instance

    if _health_checker_instance is None:
        _health_checker_instance = SupervisorHealthChecker(check_interval)

    return _health_checker_instance


def start_health_checker(check_interval=60):
    """
    Start the global health checker

    Args:
        check_interval: Seconds between health checks
    """
    checker = get_health_checker(check_interval)
    checker.start()


def stop_health_checker():
    """Stop the global health checker"""
    global _health_checker_instance

    if _health_checker_instance:
        _health_checker_instance.stop()
        _health_checker_instance = None
