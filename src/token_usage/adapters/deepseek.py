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
