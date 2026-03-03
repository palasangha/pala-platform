"""
Storage Provider Factory

Loads and instantiates storage providers based on configuration.
This allows seamless switching between different storage backends.
"""

import os
import logging
from typing import Optional
from storage_provider import StorageProvider
from sqlite_provider import SQLiteProvider

logger = logging.getLogger(__name__)


class ProviderFactory:
    """Factory for creating storage provider instances"""

    _providers = {
        'sqlite': SQLiteProvider,
        # Future providers:
        # 'postgres': PostgresProvider,
        # 'aws': AWSProvider,
        # 'local-file': LocalFileProvider,
    }

    @classmethod
    def create_provider(cls, provider_type: Optional[str] = None) -> StorageProvider:
        """
        Create a storage provider instance.

        Args:
            provider_type: Type of provider ('sqlite', 'postgres', etc.)
                          If not provided, reads from STORAGE_PROVIDER env var or defaults to 'sqlite'

        Returns:
            StorageProvider instance

        Raises:
            ValueError: If provider_type is not supported
        """
        if provider_type is None:
            provider_type = os.getenv('STORAGE_PROVIDER', 'sqlite')

        provider_type = provider_type.lower()

        if provider_type not in cls._providers:
            raise ValueError(
                f"Unsupported provider type: {provider_type}. "
                f"Supported types: {', '.join(cls._providers.keys())}"
            )

        logger.info(f"Creating {provider_type} storage provider")

        if provider_type == 'sqlite':
            db_path = os.getenv('SQLITE_DB_PATH', './storage_metadata.db')
            return SQLiteProvider(db_path=db_path)

        # Future provider creation logic:
        # elif provider_type == 'postgres':
        #     connection_string = os.getenv('DATABASE_URL')
        #     if not connection_string:
        #         raise ValueError("DATABASE_URL environment variable not set for postgres provider")
        #     return PostgresProvider(connection_string=connection_string)
        #
        # elif provider_type == 'aws':
        #     aws_region = os.getenv('AWS_REGION', 'us-east-1')
        #     s3_bucket = os.getenv('AWS_S3_BUCKET')
        #     if not s3_bucket:
        #         raise ValueError("AWS_S3_BUCKET environment variable not set for aws provider")
        #     return AWSProvider(region=aws_region, s3_bucket=s3_bucket)
        #
        # elif provider_type == 'local-file':
        #     storage_path = os.getenv('LOCAL_STORAGE_PATH', './storage/documents')
        #     return LocalFileProvider(storage_path=storage_path)

    @classmethod
    def register_provider(cls, name: str, provider_class: type) -> None:
        """
        Register a custom provider class.

        This allows extensions to add new provider implementations at runtime.

        Args:
            name: Provider name (used in STORAGE_PROVIDER env var)
            provider_class: Class that implements StorageProvider interface
        """
        if not issubclass(provider_class, StorageProvider):
            raise TypeError(f"{provider_class} does not implement StorageProvider interface")

        cls._providers[name.lower()] = provider_class
        logger.info(f"Registered custom provider: {name}")

    @classmethod
    def get_supported_providers(cls) -> list:
        """Get list of supported provider types"""
        return list(cls._providers.keys())

    @classmethod
    def reset(cls) -> None:
        """Reset to default providers (for testing)"""
        cls._providers = {
            'sqlite': SQLiteProvider,
        }


# Convenience function for getting the default provider
def get_provider() -> StorageProvider:
    """Get the configured storage provider"""
    return ProviderFactory.create_provider()
