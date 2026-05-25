from __future__ import annotations

from datetime import datetime, timezone

from token_usage.adapters.base import BaseAdapter
from token_usage.models import PlatformUsage


class OpenAIAdapter(BaseAdapter):
    async def fetch_usage(self) -> PlatformUsage:
        return PlatformUsage(
            platform="ChatGPT Plus",
            status="unconfigured",
            updated_at=datetime.now(tz=timezone.utc),
        )
