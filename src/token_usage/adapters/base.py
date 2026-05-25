from __future__ import annotations

from abc import ABC, abstractmethod

from token_usage.models import PlatformUsage


class BaseAdapter(ABC):
    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    async def fetch_usage(self) -> PlatformUsage:
        ...
