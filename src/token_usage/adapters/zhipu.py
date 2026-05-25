from __future__ import annotations

from datetime import datetime, timezone

import httpx

from token_usage.adapters.base import BaseAdapter
from token_usage.models import PlatformUsage, QuotaWindow

_TOKEN_LABELS = {0: "5小时", 1: "每周"}


class ZhipuAdapter(BaseAdapter):
    async def fetch_usage(self) -> PlatformUsage:
        api_key = self.config.get("api_key")
        if not api_key:
            return PlatformUsage(
                platform="ZhipuAI",
                status="unconfigured",
                updated_at=datetime.now(tz=timezone.utc),
            )

        base_url = self.config.get("base_url", "https://open.bigmodel.cn")
        url = f"{base_url}/api/monitor/usage/quota/limit"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                resp.raise_for_status()
                return self._parse_quota(resp.json())
        except Exception as e:
            return PlatformUsage(
                platform="ZhipuAI",
                status="error",
                error_msg=str(e),
                updated_at=datetime.now(tz=timezone.utc),
            )

    def _parse_quota(self, data: dict) -> PlatformUsage:
        limits = data.get("data", {}).get("limits", [])
        level = data.get("data", {}).get("level", "")
        quotas = []
        token_idx = 0

        for lim in limits:
            lim_type = lim.get("type")
            pct = float(lim.get("percentage", 0))

            if lim_type == "TOKENS_LIMIT":
                label = _TOKEN_LABELS.get(token_idx, f"限额{token_idx}")
                token_idx += 1
                reset_ms = lim.get("nextResetTime")
                reset_at = (
                    datetime.fromtimestamp(reset_ms / 1000, tz=timezone.utc)
                    if reset_ms
                    else None
                )
                quotas.append(QuotaWindow(
                    label=label,
                    used_percent=pct,
                    reset_at=reset_at,
                    total=f"{lim.get('usage', 0) / 1_000_000:.1f}M tokens",
                    used=f"{lim.get('currentValue', 0) / 1_000_000:.1f}M tokens",
                ))
            elif lim_type == "TIME_LIMIT":
                quotas.append(QuotaWindow(
                    label="MCP/月",
                    used_percent=pct,
                    reset_at=None,
                    total=f"{lim.get('usage', 0)} 次",
                    used=f"{lim.get('currentValue', 0)} 次",
                ))

        return PlatformUsage(
            platform="ZhipuAI",
            status="ok",
            quotas=quotas,
            extra={"level": level},
            updated_at=datetime.now(tz=timezone.utc),
        )
