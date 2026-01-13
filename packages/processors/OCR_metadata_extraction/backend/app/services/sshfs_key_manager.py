"""
SSHFS Key Manager Service

Manages SSH keys for SSHFS mounts between workers and main server.
Handles key generation, authorization, and revocation with secure permissions.
"""

import os
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SSHFSKeyManager:
    """Manages SSH keys for SSHFS authentication"""

    def __init__(self, base_path: str = None):
        """
        Initialize SSHFS Key Manager

        Args:
            base_path: Base path for SSH keys (default: /app/ssh_keys)
        """
        self.base_path = Path(base_path or os.getenv('SUPERVISOR_SSH_KEYS_PATH', '/app/ssh_keys'))
        self.deployments_path = self.base_path / 'deployments'
        self.server_sshfs_path = self.base_path / 'server_sshfs'
        self.authorized_keys_path = self.server_sshfs_path / 'authorized_keys'
        self.key_registry_path = self.server_sshfs_path / 'key_registry.json'

        # Ensure directories exist
        self._ensure_directories()

    def _ensure_directories(self):
        """Create necessary directories with proper permissions"""
        try:
            self.deployments_path.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.server_sshfs_path.mkdir(parents=True, exist_ok=True, mode=0o700)

            # Create authorized_keys if it doesn't exist
            if not self.authorized_keys_path.exists():
                self.authorized_keys_path.touch(mode=0o600)

            # Create key registry if it doesn't exist
            if not self.key_registry_path.exists():
                self.key_registry_path.write_text(json.dumps({}, indent=2))
                self.key_registry_path.chmod(0o600)

            logger.info(f"SSHFS key directories initialized at {self.base_path}")
        except Exception as e:
            logger.error(f"Failed to create SSHFS key directories: {e}")
            raise

    def generate_deployment_key(self, deployment_id: str) -> Dict:
        """
        Generate ED25519 SSH key pair for a deployment

        Args:
            deployment_id: Unique deployment identifier

        Returns:
            Dictionary with:
                - private_key_path: Path to private key
                - public_key_path: Path to public key
                - public_key: Public key content
                - fingerprint: SSH key fingerprint
        """
        try:
            # Create deployment directory
            deployment_dir = self.deployments_path / deployment_id
            deployment_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

            private_key_path = deployment_dir / 'sshfs_key'
            public_key_path = deployment_dir / 'sshfs_key.pub'

            # Generate ED25519 key pair (modern, fast, secure)
            cmd = [
                'ssh-keygen',
                '-t', 'ed25519',
                '-f', str(private_key_path),
                '-N', '',  # No passphrase
                '-C', f'deployment-{deployment_id}'  # Comment
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            # Set proper permissions
            private_key_path.chmod(0o600)
            public_key_path.chmod(0o644)

            # Read public key
            public_key = public_key_path.read_text().strip()

            # Get fingerprint
            fingerprint = self._get_key_fingerprint(public_key_path)

            logger.info(f"Generated SSHFS key for deployment {deployment_id}: {fingerprint}")

            return {
                'private_key_path': str(private_key_path),
                'public_key_path': str(public_key_path),
                'public_key': public_key,
                'fingerprint': fingerprint,
                'deployment_id': deployment_id
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to generate SSH key for deployment {deployment_id}: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"Error generating deployment key: {e}")
            raise

    def _get_key_fingerprint(self, key_path: Path) -> str:
        """
        Get SSH key fingerprint

        Args:
            key_path: Path to public key file

        Returns:
            Key fingerprint (SHA256)
        """
        try:
            cmd = ['ssh-keygen', '-lf', str(key_path), '-E', 'sha256']
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            # Output format: "256 SHA256:fingerprint comment (ED25519)"
            parts = result.stdout.strip().split()
            if len(parts) >= 2:
                return parts[1]  # SHA256:...
            return ''
        except Exception as e:
            logger.warning(f"Failed to get key fingerprint: {e}")
            return ''

    def authorize_key(self, deployment_id: str, public_key: str) -> bool:
        """
        Add public key to SSHFS user's authorized_keys with restrictions

        Args:
            deployment_id: Deployment identifier
            public_key: SSH public key content

        Returns:
            True if successful
        """
        try:
            # Read current authorized_keys
            if self.authorized_keys_path.exists():
                current_content = self.authorized_keys_path.read_text()
            else:
                current_content = ''

            # Check if key already authorized (prevent duplicates)
            if f'deployment-{deployment_id}' in current_content:
                logger.warning(f"Key for deployment {deployment_id} already authorized")
                return True

            # Build authorized_keys entry with restrictions
            # Restrict to internal-sftp only, no port forwarding, no shell
            restrictions = [
                'command="internal-sftp"',
                'no-port-forwarding',
                'no-X11-forwarding',
                'no-agent-forwarding',
                'no-pty'
            ]

            entry = f"{','.join(restrictions)} {public_key}\n"

            # Append to authorized_keys
            with self.authorized_keys_path.open('a') as f:
                f.write(entry)

            # Set proper permissions
            self.authorized_keys_path.chmod(0o600)

            # Update key registry
            self._update_key_registry(deployment_id, public_key, 'authorized')

            logger.info(f"Authorized SSHFS key for deployment {deployment_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to authorize key for deployment {deployment_id}: {e}")
            return False

    def revoke_key(self, deployment_id: str) -> bool:
        """
        Remove public key from authorized_keys

        Args:
            deployment_id: Deployment identifier

        Returns:
            True if successful
        """
        try:
            if not self.authorized_keys_path.exists():
                logger.warning("authorized_keys file does not exist")
                return False

            # Read authorized_keys
            lines = self.authorized_keys_path.read_text().splitlines()

            # Filter out the deployment's key
            filtered_lines = [
                line for line in lines
                if f'deployment-{deployment_id}' not in line
            ]

            # Write back filtered content
            self.authorized_keys_path.write_text('\n'.join(filtered_lines) + '\n' if filtered_lines else '')
            self.authorized_keys_path.chmod(0o600)

            # Update key registry
            self._update_key_registry(deployment_id, None, 'revoked')

            logger.info(f"Revoked SSHFS key for deployment {deployment_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to revoke key for deployment {deployment_id}: {e}")
            return False

    def _update_key_registry(self, deployment_id: str, public_key: Optional[str], status: str):
        """
        Update key registry with deployment key information

        Args:
            deployment_id: Deployment identifier
            public_key: Public key content (None for revocation)
            status: 'authorized' or 'revoked'
        """
        try:
            # Read current registry
            if self.key_registry_path.exists():
                registry = json.loads(self.key_registry_path.read_text())
            else:
                registry = {}

            if status == 'authorized' and public_key:
                # Extract fingerprint from public key
                fingerprint = public_key.split()[1] if len(public_key.split()) > 1 else ''

                registry[deployment_id] = {
                    'fingerprint': fingerprint,
                    'status': status,
                    'authorized_at': datetime.utcnow().isoformat(),
                    'last_updated': datetime.utcnow().isoformat()
                }
            elif status == 'revoked':
                if deployment_id in registry:
                    registry[deployment_id]['status'] = status
                    registry[deployment_id]['revoked_at'] = datetime.utcnow().isoformat()
                    registry[deployment_id]['last_updated'] = datetime.utcnow().isoformat()

            # Write updated registry
            self.key_registry_path.write_text(json.dumps(registry, indent=2))
            self.key_registry_path.chmod(0o600)

        except Exception as e:
            logger.warning(f"Failed to update key registry: {e}")

    def get_private_key_path(self, deployment_id: str) -> str:
        """
        Get path to deployment's private key

        Args:
            deployment_id: Deployment identifier

        Returns:
            Path to private key file
        """
        return str(self.deployments_path / deployment_id / 'sshfs_key')

    def get_public_key_path(self, deployment_id: str) -> str:
        """
        Get path to deployment's public key

        Args:
            deployment_id: Deployment identifier

        Returns:
            Path to public key file
        """
        return str(self.deployments_path / deployment_id / 'sshfs_key.pub')

    def key_exists(self, deployment_id: str) -> bool:
        """
        Check if key exists for deployment

        Args:
            deployment_id: Deployment identifier

        Returns:
            True if key exists
        """
        private_key = Path(self.get_private_key_path(deployment_id))
        return private_key.exists()

    def cleanup_deployment_keys(self, deployment_id: str) -> bool:
        """
        Remove all keys for a deployment (used during deployment deletion)

        Args:
            deployment_id: Deployment identifier

        Returns:
            True if successful
        """
        try:
            # Revoke from authorized_keys
            self.revoke_key(deployment_id)

            # Delete key files
            deployment_dir = self.deployments_path / deployment_id
            if deployment_dir.exists():
                import shutil
                shutil.rmtree(deployment_dir)
                logger.info(f"Cleaned up SSHFS keys for deployment {deployment_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to cleanup keys for deployment {deployment_id}: {e}")
            return False

    def get_key_info(self, deployment_id: str) -> Optional[Dict]:
        """
        Get key information from registry

        Args:
            deployment_id: Deployment identifier

        Returns:
            Key info dictionary or None if not found
        """
        try:
            if self.key_registry_path.exists():
                registry = json.loads(self.key_registry_path.read_text())
                return registry.get(deployment_id)
            return None
        except Exception as e:
            logger.warning(f"Failed to get key info: {e}")
            return None
