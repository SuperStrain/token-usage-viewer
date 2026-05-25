from __future__ import annotations

from datetime import datetime, timezone

import httpx

from token_usage.adapters.base import BaseAdapter
from token_usage.models import PlatformUsage


class DeepSeekAdapter(BaseAdapter):
    async def fetch_usage(self) -> PlatformUsage:
        api_key = self.config.get("api_key")
        if not api_key:
            return PlatformUsage(
                platform="DeepSeek",
                status="unconfigured",
                updated_at=datetime.now(tz=timezone.utc),
            )

        base_url = self.config.get("base_url", "https://api.deepseek.com")
        url = f"{base_url}/user/balance"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                resp.raise_for_status()
                return self._parse_balance(resp.json())
        except Exception as e:
            return PlatformUsage(
                platform="DeepSeek",
                status="error",
                error_msg=str(e),
                updated_at=datetime.now(tz=timezone.utc),
            )

    def _parse_balance(self, data: dict) -> PlatformUsage:
        infos = data.get("balance_infos", [])
        if not infos:
            return PlatformUsage(
                platform="DeepSeek",
                status="error",
                error_msg="No balance info returned",
                updated_at=datetime.now(tz=timezone.utc),
            )

        info = infos[0]
        currency = info.get("currency", "CNY")
        total = info.get("total_balance", "0")
        symbol = "¥" if currency == "CNY" else "$"

        return PlatformUsage(
            platform="DeepSeek",
            status="ok",
            balance=f"{symbol}{total} {currency}",
            updated_at=datetime.now(tz=timezone.utc),
        )
