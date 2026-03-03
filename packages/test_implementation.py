#!/usr/bin/env python3
"""
Quick smoke test for storage-agent provider architecture.
"""

import asyncio
from datetime import datetime, timezone
import importlib
from pathlib import Path
import sys

root_dir = Path(__file__).parent
storage_agent_dir = root_dir / "PalaAgents" / "storage-agent"
sys.path.insert(0, str(storage_agent_dir))


async def test_provider_and_metadata() -> None:
    MetadataDB = importlib.import_module("metadata_db").MetadataDB
    LocalProvider = importlib.import_module("providers.local_provider").LocalProvider

    data_dir = storage_agent_dir / "data"
    content_dir = data_dir / "smoke_content"
    metadata_path = data_dir / "smoke_metadata.db"

    provider = LocalProvider(
        provider_id="local-provider",
        config={"base_path": str(content_dir)},
    )
    metadata_db = MetadataDB(str(metadata_path))

    payload = "Smoke test content from provider architecture"
    content_bytes = payload.encode("utf-8")
    file_hash = metadata_db.calculate_hash(content_bytes)
    content_id = f"smoke-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    location = await provider.write(
        content_id=content_id,
        content=content_bytes,
        metadata={
            "content_type": "document",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    metadata_db.insert(
        content_id=content_id,
        content_type="document",
        file_hash=file_hash,
        file_size=len(content_bytes),
        provider_id="local-provider",
        storage_location=location,
        metadata={"source": "smoke-test"},
    )

    row = metadata_db.get_metadata(content_id)
    assert row is not None

    loaded = await provider.read(content_id, location)
    assert loaded.decode("utf-8") == payload

    print("✅ provider + metadata smoke test passed")


if __name__ == "__main__":
    asyncio.run(test_provider_and_metadata())
