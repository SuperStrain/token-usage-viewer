from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from token_usage.adapters.base import BaseAdapter
from token_usage.models import PlatformUsage, QuotaWindow


class OpenAIAdapter(BaseAdapter):
    async def fetch_usage(self) -> PlatformUsage:
        access_token = self.config.get("access_token")
        if not access_token:
            return PlatformUsage(
                platform="OpenAI",
                status="unconfigured",
                updated_at=datetime.now(tz=timezone.utc),
            )

        url = "https://chatgpt.com/backend-api/wham/usage"
        headers = {"Authorization": f"Bearer {access_token}"}
        account_id = self.config.get("account_id")
        if account_id:
            headers["ChatGPT-Account-Id"] = account_id

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                return self._parse_usage(resp.json())
        except Exception as e:
            return PlatformUsage(
                platform="OpenAI",
                status="error",
                error_msg=str(e),
                updated_at=datetime.now(tz=timezone.utc),
            )

    def _parse_usage(self, data: dict) -> PlatformUsage:
        now = datetime.now(tz=timezone.utc)
        rate_limit = data.get("rate_limit", {})
        plan = data.get("plan_type", "unknown")
        quotas = []

        primary = rate_limit.get("primary_window")
        if primary:
            reset_after = primary.get("reset_after_seconds", 0)
            quotas.append(QuotaWindow(
                label="5小时限额",
                used_percent=float(primary.get("used_percent", 0)),
                reset_at=now + timedelta(seconds=reset_after) if reset_after else None,
            ))

        secondary = rate_limit.get("secondary_window")
        if secondary:
            reset_after = secondary.get("reset_after_seconds", 0)
            quotas.append(QuotaWindow(
                label="每周限额",
                used_percent=float(secondary.get("used_percent", 0)),
                reset_at=now + timedelta(seconds=reset_after) if reset_after else None,
            ))

        return PlatformUsage(
            platform="OpenAI",
            status="ok",
            quotas=quotas,
            extra={"plan": plan},
            updated_at=now,
        )
