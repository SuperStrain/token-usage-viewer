from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import httpx

from token_usage.adapters.base import BaseAdapter
from token_usage.models import PlatformUsage, QuotaWindow

_PATTERN = re.compile(
    r"(?:rolling|weekly|monthly)Usage:\$R\[\d+\]=\(\{usagePercent:(\d+),resetInSec:(\d+)\}\)"
)


class OpenCodeAdapter(BaseAdapter):
    async def fetch_usage(self) -> PlatformUsage:
        workspace_id = self.config.get("workspace_id")
        auth_cookie = self.config.get("auth_cookie")
        if not workspace_id or not auth_cookie:
            return PlatformUsage(
                platform="OpenCode Go",
                status="unconfigured",
                updated_at=datetime.now(tz=timezone.utc),
            )

        url = f"https://opencode.ai/workspace/{workspace_id}/go"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) token-usage-viewer/0.1",
                        "Accept": "text/html",
                        "Cookie": f"auth={auth_cookie}",
                    },
                )
                resp.raise_for_status()
                return self._parse_html(resp.text)
        except Exception as e:
            return PlatformUsage(
                platform="OpenCode Go",
                status="error",
                error_msg=str(e),
                updated_at=datetime.now(tz=timezone.utc),
            )

    def _parse_html(self, html: str) -> PlatformUsage:
        matches = _PATTERN.findall(html)
        if len(matches) < 3:
            return PlatformUsage(
                platform="OpenCode Go",
                status="error",
                error_msg="Failed to parse usage data from page",
                updated_at=datetime.now(tz=timezone.utc),
            )

        now = datetime.now(tz=timezone.utc)
        labels = ["滚动(5h)", "每周", "每月"]
        quotas = []
        for i, (pct_str, sec_str) in enumerate(matches[:3]):
            quotas.append(QuotaWindow(
                label=labels[i],
                used_percent=float(pct_str),
                reset_at=now + timedelta(seconds=int(sec_str)),
            ))

        return PlatformUsage(
            platform="OpenCode Go",
            status="ok",
            quotas=quotas,
            updated_at=now,
        )
