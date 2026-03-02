from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ProviderSpec:
    provider_id: str
    backend_name: str
    backend_type: str
    preferred_default: bool = False
    enabled: bool = True
    notes: Optional[str] = None
