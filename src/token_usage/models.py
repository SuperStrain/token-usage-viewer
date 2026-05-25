from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class QuotaWindow:
    label: str
    used_percent: float
    reset_at: datetime | None = None
    total: str | None = None
    used: str | None = None


@dataclass
class PlatformUsage:
    platform: str
    status: str
    error_msg: str | None = None
    balance: str | None = None
    quotas: list[QuotaWindow] = field(default_factory=list)
    extra: dict | None = None
    updated_at: datetime | None = None
