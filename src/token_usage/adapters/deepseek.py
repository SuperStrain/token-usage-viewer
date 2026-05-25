from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx

from token_usage.adapters.base import BaseAdapter
from token_usage.models import PlatformUsage


class DeepSeekAdapter(BaseAdapter):
    async def fetch_usage(self) -> PlatformUsage:
        platform_token = self.config.get("platform_token")
        if platform_token:
            return await self._fetch_platform(platform_token)

        api_key = self.config.get("api_key")
        if not api_key:
            return PlatformUsage(
                platform="DeepSeek",
                status="unconfigured",
                updated_at=datetime.now(tz=timezone.utc),
            )

        return await self._fetch_balance(api_key)

    async def _fetch_platform(self, token: str) -> PlatformUsage:
        base = "https://platform.deepseek.com"
        headers = {
            "Authorization": f"Bearer {token}",
            "x-app-version": "1.0.0",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) token-usage-viewer/0.1",
        }
        cookie = self.config.get("cookie")
        if cookie:
            headers["Cookie"] = cookie

        now = datetime.now(tz=timezone.utc)
        month = now.month
        year = now.year

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                summary_task = client.get(
                    f"{base}/api/v0/users/get_user_summary",
                    headers=headers,
                )
                amount_task = client.get(
                    f"{base}/api/v0/usage/amount",
                    params={"month": month, "year": year},
                    headers=headers,
                )
                summary_resp, amount_resp = await asyncio.gather(
                    summary_task, amount_task, return_exceptions=True,
                )

            if isinstance(summary_resp, Exception):
                return await self._fallback_balance()

            summary_resp.raise_for_status()
            result = self._parse_platform_summary(summary_resp.json())

            if not isinstance(amount_resp, Exception):
                amount_resp.raise_for_status()
                models = self._parse_usage_amount(amount_resp.json())
                if models:
                    result.extra["models"] = models

            return result

        except Exception:
            return await self._fallback_balance()

    async def _fallback_balance(self) -> PlatformUsage:
        api_key = self.config.get("api_key")
        if not api_key:
            return PlatformUsage(
                platform="DeepSeek",
                status="error",
                error_msg="Platform API failed, no api_key for fallback",
                updated_at=datetime.now(tz=timezone.utc),
            )
        return await self._fetch_balance(api_key)

    async def _fetch_balance(self, api_key: str) -> PlatformUsage:
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

    @staticmethod
    def _format_tokens(amount_str: str) -> str:
        val = float(amount_str)
        if val >= 1_000_000:
            return f"{val / 1_000_000:.1f}M"
        if val >= 1_000:
            return f"{val / 1_000:.1f}K"
        return f"{val:.0f}"

    def _parse_platform_summary(self, data: dict) -> PlatformUsage:
        now = datetime.now(tz=timezone.utc)
        biz = data.get("data", {}).get("biz_data", {})

        wallets = biz.get("normal_wallets", [])
        wallet = wallets[0] if wallets else {}
        currency = wallet.get("currency", "CNY")
        symbol = "¥" if currency == "CNY" else "$"
        balance_val = wallet.get("balance", "0")
        balance = f"{symbol}{float(balance_val):.2f} {currency}"

        monthly_costs = biz.get("monthly_costs", [])
        cost = monthly_costs[0] if monthly_costs else {}
        cost_amount = float(cost.get("amount", "0"))
        cost_currency = cost.get("currency", currency)
        cost_symbol = "¥" if cost_currency == "CNY" else "$"
        monthly_cost = f"{cost_symbol}{cost_amount:.2f} {cost_currency}"

        monthly_token_usage = biz.get("monthly_token_usage", "0")
        available = biz.get("total_available_token_estimation", "0")

        return PlatformUsage(
            platform="DeepSeek",
            status="ok",
            balance=balance,
            extra={
                "monthly_cost": monthly_cost,
                "monthly_tokens": self._format_tokens(monthly_token_usage),
                "available_tokens": self._format_tokens(available),
            },
            updated_at=now,
        )

    def _parse_usage_amount(self, data: dict) -> list[dict]:
        total_list = data.get("data", {}).get("biz_data", {}).get("total", [])
        models = []
        for item in total_list:
            model_name = item.get("model", "")
            usage_items = item.get("usage", [])
            token_total = 0
            requests = 0
            for u in usage_items:
                amt = int(u.get("amount", "0"))
                if u["type"] == "REQUEST":
                    requests = amt
                elif u["type"] in (
                    "PROMPT_CACHE_HIT_TOKEN",
                    "PROMPT_CACHE_MISS_TOKEN",
                    "RESPONSE_TOKEN",
                ):
                    token_total += amt
            if token_total == 0 and requests == 0:
                continue
            short = model_name.replace("deepseek-", "")
            models.append({
                "name": short,
                "tokens": self._format_tokens(str(token_total)),
                "requests": requests,
            })
        return models
