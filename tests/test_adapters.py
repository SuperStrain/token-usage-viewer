import pytest
from token_usage.adapters.opencode import OpenCodeAdapter
from token_usage.adapters.openai import OpenAIAdapter
from token_usage.adapters.deepseek import DeepSeekAdapter
from token_usage.adapters.zhipu import ZhipuAdapter


def _make_opencode_html(rolling_pct, rolling_sec, weekly_pct, weekly_sec, monthly_pct, monthly_sec):
    return f"""
    <html><script>
    rollingUsage:$R[30]={{status:"ok",resetInSec:{rolling_sec},usagePercent:{rolling_pct}}};
    weeklyUsage:$R[31]={{status:"ok",resetInSec:{weekly_sec},usagePercent:{weekly_pct}}};
    monthlyUsage:$R[32]={{status:"ok",resetInSec:{monthly_sec},usagePercent:{monthly_pct}}};
    </script></html>
    """


def test_opencode_parse_success():
    html = _make_opencode_html(33, 7200, 25, 86400, 12, 259200)
    adapter = OpenCodeAdapter({
        "workspace_id": "wrk_test",
        "auth_cookie": "test_cookie",
    })
    result = adapter._parse_html(html)
    assert result.status == "ok"
    assert len(result.quotas) == 3
    assert result.quotas[0].label == "滚动(5h)"
    assert result.quotas[0].used_percent == 33.0
    assert result.quotas[1].label == "每周"
    assert result.quotas[1].used_percent == 25.0
    assert result.quotas[2].label == "每月"
    assert result.quotas[2].used_percent == 12.0


@pytest.mark.asyncio
async def test_opencode_unconfigured():
    adapter = OpenCodeAdapter({})
    result = await adapter.fetch_usage()
    assert result.status == "unconfigured"


def test_opencode_parse_invalid_html():
    adapter = OpenCodeAdapter({
        "workspace_id": "wrk_test",
        "auth_cookie": "test_cookie",
    })
    result = adapter._parse_html("<html>no data here</html>")
    assert result.status == "error"


@pytest.mark.asyncio
async def test_deepseek_unconfigured():
    adapter = DeepSeekAdapter({})
    result = await adapter.fetch_usage()
    assert result.status == "unconfigured"


def test_deepseek_parse_balance():
    adapter = DeepSeekAdapter({"api_key": "sk-test"})
    data = {
        "is_available": True,
        "balance_infos": [
            {
                "currency": "CNY",
                "total_balance": "79.76",
                "granted_balance": "10.00",
                "topped_up_balance": "69.76",
            }
        ],
    }
    result = adapter._parse_balance(data)
    assert result.status == "ok"
    assert result.balance == "¥79.76 CNY"
    assert len(result.quotas) == 0


@pytest.mark.asyncio
async def test_zhipu_unconfigured():
    adapter = ZhipuAdapter({})
    result = await adapter.fetch_usage()
    assert result.status == "unconfigured"


def test_zhipu_parse_quota():
    adapter = ZhipuAdapter({"api_key": "test"})
    data = {
        "code": 200,
        "data": {
            "limits": [
                {
                    "type": "TOKENS_LIMIT",
                    "usage": 5000000,
                    "currentValue": 2200000,
                    "percentage": 44,
                    "nextResetTime": 1748200000000,
                    "unit": 3,
                    "number": 5,
                },
                {
                    "type": "TOKENS_LIMIT",
                    "usage": 12000000,
                    "currentValue": 6400000,
                    "percentage": 53,
                    "nextResetTime": 1748600000000,
                    "unit": 3,
                    "number": 5,
                },
                {
                    "type": "TIME_LIMIT",
                    "usage": 1000,
                    "currentValue": 72,
                    "remaining": 928,
                    "percentage": 7,
                },
            ],
            "level": "pro",
        },
    }
    result = adapter._parse_quota(data)
    assert result.status == "ok"
    assert result.extra["level"] == "pro"
    assert len(result.quotas) == 3
    assert result.quotas[0].label == "5小时"
    assert result.quotas[0].used_percent == 44.0
    assert result.quotas[1].label == "每周"
    assert result.quotas[1].used_percent == 53.0
    assert result.quotas[2].label == "MCP/月"
    assert result.quotas[2].used_percent == 7.0


@pytest.mark.asyncio
async def test_openai_unconfigured():
    adapter = OpenAIAdapter({})
    result = await adapter.fetch_usage()
    assert result.status == "unconfigured"


def test_openai_parse_usage():
    adapter = OpenAIAdapter({"access_token": "test"})
    data = {
        "plan_type": "plus",
        "rate_limit": {
            "allowed": True,
            "limit_reached": False,
            "primary_window": {
                "used_percent": 45,
                "limit_window_seconds": 18000,
                "reset_after_seconds": 7200,
            },
            "secondary_window": None,
        },
    }
    result = adapter._parse_usage(data)
    assert result.status == "ok"
    assert result.extra["plan"] == "plus"
    assert len(result.quotas) == 1
    assert result.quotas[0].label == "5小时限额"
    assert result.quotas[0].used_percent == 45.0


def test_openai_parse_with_weekly():
    adapter = OpenAIAdapter({"access_token": "test"})
    data = {
        "plan_type": "pro",
        "rate_limit": {
            "allowed": True,
            "limit_reached": False,
            "primary_window": {
                "used_percent": 30,
                "limit_window_seconds": 18000,
                "reset_after_seconds": 3600,
            },
            "secondary_window": {
                "used_percent": 20,
                "limit_window_seconds": 604800,
                "reset_after_seconds": 86400,
            },
        },
    }
    result = adapter._parse_usage(data)
    assert result.status == "ok"
    assert len(result.quotas) == 2
    assert result.quotas[0].label == "5小时限额"
    assert result.quotas[1].label == "每周限额"
    assert result.quotas[1].used_percent == 20.0


def test_deepseek_parse_platform_summary():
    adapter = DeepSeekAdapter({"api_key": "sk-test", "platform_token": "tok"})
    data = {
        "code": 0,
        "data": {
            "biz_code": 0,
            "biz_data": {
                "current_token": 10000000,
                "monthly_usage": "188852655",
                "normal_wallets": [
                    {
                        "currency": "CNY",
                        "balance": "79.7625591200000000",
                        "token_estimation": "26587519",
                    }
                ],
                "bonus_wallets": [],
                "total_available_token_estimation": "26587519",
                "monthly_costs": [
                    {
                        "currency": "CNY",
                        "amount": "36.2374408800000000",
                    }
                ],
                "monthly_token_usage": "188852655",
            },
        },
    }
    result = adapter._parse_platform_summary(data)
    assert result.status == "ok"
    assert result.balance == "¥79.76 CNY"
    assert result.extra["monthly_cost"] == "¥36.24 CNY"
    assert result.extra["monthly_tokens"] == "188.9M"
    assert result.extra["available_tokens"] == "26.6M"


def test_deepseek_parse_usage_amount():
    adapter = DeepSeekAdapter({"api_key": "sk-test", "platform_token": "tok"})
    data = {
        "code": 0,
        "data": {
            "biz_data": {
                "total": [
                    {
                        "model": "deepseek-v4-pro",
                        "usage": [
                            {"type": "PROMPT_TOKEN", "amount": "0"},
                            {"type": "PROMPT_CACHE_HIT_TOKEN", "amount": "176685824"},
                            {"type": "PROMPT_CACHE_MISS_TOKEN", "amount": "6870490"},
                            {"type": "RESPONSE_TOKEN", "amount": "1751641"},
                            {"type": "REQUEST", "amount": "2483"},
                        ],
                    },
                    {
                        "model": "deepseek-v4-flash",
                        "usage": [
                            {"type": "PROMPT_TOKEN", "amount": "0"},
                            {"type": "PROMPT_CACHE_HIT_TOKEN", "amount": "2936064"},
                            {"type": "PROMPT_CACHE_MISS_TOKEN", "amount": "577014"},
                            {"type": "RESPONSE_TOKEN", "amount": "31622"},
                            {"type": "REQUEST", "amount": "85"},
                        ],
                    },
                    {
                        "model": "deepseek-chat & deepseek-reasoner",
                        "usage": [
                            {"type": "PROMPT_TOKEN", "amount": "0"},
                            {"type": "PROMPT_CACHE_HIT_TOKEN", "amount": "0"},
                            {"type": "PROMPT_CACHE_MISS_TOKEN", "amount": "0"},
                            {"type": "RESPONSE_TOKEN", "amount": "0"},
                            {"type": "REQUEST", "amount": "0"},
                        ],
                    },
                ],
            },
        },
    }
    result = adapter._parse_usage_amount(data)
    assert len(result) == 2
    assert result[0]["name"] == "v4-pro"
    assert result[0]["tokens"] == "185.3M"
    assert result[0]["requests"] == 2483
    assert result[1]["name"] == "v4-flash"
    assert result[1]["tokens"] == "3.5M"
    assert result[1]["requests"] == 85
