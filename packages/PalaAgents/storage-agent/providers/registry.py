from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .azure_provider import AzureProvider
from .base_provider import BaseStorageProvider
from .gcs_provider import GCSProvider
from .local_provider import LocalProvider
from .s3_provider import S3Provider
from .sqlite_provider import SQLiteProvider


def build_provider_instances(storage_dir: Path) -> Dict[str, BaseStorageProvider]:
    providers: Dict[str, BaseStorageProvider] = {}

    providers["local-provider"] = LocalProvider(
        provider_id="local-provider",
        config={"base_path": str(storage_dir / "content")},
    )

    providers["sqlite-provider"] = SQLiteProvider(
        provider_id="sqlite-provider",
        config={"db_path": str(storage_dir / "content_blobs.db")},
    )

    providers["s3-provider"] = S3Provider(provider_id="s3-provider", config={})
    providers["gcs-provider"] = GCSProvider(provider_id="gcs-provider", config={})
    providers["azure-provider"] = AzureProvider(provider_id="azure-provider", config={})

    return providers


def build_provider_catalog(providers: Dict[str, BaseStorageProvider]) -> Dict[str, Dict[str, Any]]:
    catalog: Dict[str, Dict[str, Any]] = {}

    for provider_id in providers.keys():
        if provider_id == "local-provider":
            catalog[provider_id] = {
                "provider_id": provider_id,
                "backend_name": "local-primary",
                "provider_type": "local",
                "enabled": True,
                "is_default": True,
                "notes": None,
            }
        elif provider_id == "sqlite-provider":
            catalog[provider_id] = {
                "provider_id": provider_id,
                "backend_name": "sqlite-primary",
                "provider_type": "sqlite",
                "enabled": True,
                "is_default": False,
                "notes": "Stores content blobs in SQLite.",
            }
        elif provider_id == "s3-provider":
            catalog[provider_id] = {
                "provider_id": provider_id,
                "backend_name": "s3-primary",
                "provider_type": "s3",
                "enabled": False,
                "is_default": False,
                "notes": "Provider scaffolded, implementation pending.",
            }
        elif provider_id == "gcs-provider":
            catalog[provider_id] = {
                "provider_id": provider_id,
                "backend_name": "gcs-primary",
                "provider_type": "gcs",
                "enabled": False,
                "is_default": False,
                "notes": "Provider scaffolded, implementation pending.",
            }
        elif provider_id == "azure-provider":
            catalog[provider_id] = {
                "provider_id": provider_id,
                "backend_name": "azure-primary",
                "provider_type": "azure",
                "enabled": False,
                "is_default": False,
                "notes": "Provider scaffolded, implementation pending.",
            }

    return catalog


def provider_id_from_backend(catalog: Dict[str, Dict[str, Any]], backend_name: str) -> str | None:
    for provider_id, provider in catalog.items():
        if provider.get("backend_name") == backend_name:
            return provider_id
    return None


def resolve_provider_id_from_params(
    params: Dict[str, Any],
    catalog: Dict[str, Dict[str, Any]],
    default_provider_id: str,
) -> str:
    explicit_provider = params.get("provider") or params.get("provider_id")
    if explicit_provider:
        provider_id = str(explicit_provider)
    else:
        explicit_backend = params.get("backend")
        if explicit_backend:
            backend_value = str(explicit_backend)
            provider_id = provider_id_from_backend(catalog, backend_value)
            if not provider_id:
                provider_id = next(
                    (
                        current_provider_id
                        for current_provider_id, info in catalog.items()
                        if info.get("provider_type") == backend_value
                    ),
                    None,
                )
            if not provider_id:
                raise ValueError(f"Unknown backend: {backend_value}")
        else:
            provider_id = default_provider_id

    info = catalog.get(provider_id)
    if not info:
        raise ValueError(f"Unknown provider: {provider_id}")
    if not info.get("enabled"):
        raise ValueError(f"Provider not enabled: {provider_id}")

    return provider_id
