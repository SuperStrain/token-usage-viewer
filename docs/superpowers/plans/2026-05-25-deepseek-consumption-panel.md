# DeepSeek 消费面板实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 DeepSeek 平台卡片新增消费和用量展示，通过控制台内部 API 获取月度消费、按模型 token 用量等数据。

**Architecture:** 在现有 `DeepSeekAdapter` 中新增两个控制台 API 调用（`get_user_summary` + `usage/amount`），与原有 `/user/balance` 形成三级降级链。消费数据通过 `PlatformUsage.extra` 字段传递，UI 层在 `PlatformCard` 中新增 `card-detail` 样式渲染模型明细。

**Tech Stack:** Python 3.11+, httpx, Textual, pytest + pytest-asyncio

---

## File Structure

| 文件 | 操作 | 职责 |
|------|------|------|
| `src/token_usage/adapters/deepseek.py` | 修改 | 新增控制台 API 调用、解析、降级逻辑 |
| `src/token_usage/widgets/platform_card.py` | 修改 | 新增 `card-detail` CSS、渲染消费 extra |
| `config.example.yaml` | 修改 | 新增 `platform_token`、`cookie` 配置项 |
| `tests/test_adapters.py` | 修改 | 新增解析函数的单元测试 |

---

### Task 1: 新增 `_format_tokens` 工具函数和 `_parse_platform_summary` 解析函数

**Files:**
- Modify: `src/token_usage/adapters/deepseek.py`
- Test: `tests/test_adapters.py`

- [ ] **Step 1: 编写 `_parse_platform_summary` 的失败测试**

在 `tests/test_adapters.py` 末尾追加：

```python
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
    assert result.extra["monthly_tokens"] == "185.3M"
    assert result.extra["available_tokens"] == "26.6M"
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/test_adapters.py::test_deepseek_parse_platform_summary -v`
Expected: FAIL (AttributeError: 'DeepSeekAdapter' has no attribute '_parse_platform_summary')

- [ ] **Step 3: 实现 `_format_tokens` 和 `_parse_platform_summary`**

在 `src/token_usage/adapters/deepseek.py` 中，在 `_parse_balance` 方法之后追加：

```python
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
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/test_adapters.py::test_deepseek_parse_platform_summary -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/token_usage/adapters/deepseek.py tests/test_adapters.py
git commit -m "feat(deepseek): add _parse_platform_summary with token formatting"
```

---

### Task 2: 新增 `_parse_usage_amount` 解析函数

**Files:**
- Modify: `src/token_usage/adapters/deepseek.py`
- Test: `tests/test_adapters.py`

- [ ] **Step 1: 编写 `_parse_usage_amount` 的失败测试**

在 `tests/test_adapters.py` 末尾追加：

```python
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
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/test_adapters.py::test_deepseek_parse_usage_amount -v`
Expected: FAIL (AttributeError)

- [ ] **Step 3: 实现 `_parse_usage_amount`**

在 `src/token_usage/adapters/deepseek.py` 中，`_parse_platform_summary` 方法之后追加：

```python
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
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/test_adapters.py::test_deepseek_parse_usage_amount -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/token_usage/adapters/deepseek.py tests/test_adapters.py
git commit -m "feat(deepseek): add _parse_usage_amount for model-level breakdown"
```

---

### Task 3: 改造 `fetch_usage` 集成双接口调用与降级

**Files:**
- Modify: `src/token_usage/adapters/deepseek.py`
- Modify: `pyproject.toml`（添加 pytest-httpx 依赖）

- [ ] **Step 0: 安装 pytest-httpx**

Run: `uv add --dev pytest-httpx`

- [ ] **Step 1: 编写集成测试（mock HTTP 调用）**

在 `tests/test_adapters.py` 末尾追加：

```python
@pytest.mark.asyncio
async def test_deepseek_fetch_with_platform_token(httpx_mock):
    httpx_mock.add_response(
        url="https://platform.deepseek.com/api/v0/users/get_user_summary",
        json={
            "code": 0,
            "data": {
                "biz_code": 0,
                "biz_data": {
                    "normal_wallets": [{"currency": "CNY", "balance": "50.00"}],
                    "monthly_costs": [{"currency": "CNY", "amount": "10.50"}],
                    "monthly_token_usage": "5000000",
                    "total_available_token_estimation": "20000000",
                },
            },
        },
    )
    httpx_mock.add_response(
        url__regex=r"https://platform\.deepseek\.com/api/v0/usage/amount\?month=\d+&year=\d+",
        json={
            "code": 0,
            "data": {
                "biz_data": {
                    "total": [
                        {
                            "model": "deepseek-v4-pro",
                            "usage": [
                                {"type": "PROMPT_CACHE_HIT_TOKEN", "amount": "4000000"},
                                {"type": "PROMPT_CACHE_MISS_TOKEN", "amount": "500000"},
                                {"type": "RESPONSE_TOKEN", "amount": "500000"},
                                {"type": "REQUEST", "amount": "100"},
                            ],
                        },
                    ],
                },
            },
        },
    )
    adapter = DeepSeekAdapter({"platform_token": "tok123"})
    result = await adapter.fetch_usage()
    assert result.status == "ok"
    assert result.balance == "¥50.00 CNY"
    assert result.extra["monthly_cost"] == "¥10.50 CNY"
    assert result.extra["monthly_tokens"] == "5.0M"
    assert len(result.extra["models"]) == 1
    assert result.extra["models"][0]["name"] == "v4-pro"
```

注意：此测试依赖 `pytest-httpx` 包。检查是否已安装，如未安装需添加。

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/test_adapters.py::test_deepseek_fetch_with_platform_token -v`
Expected: FAIL (当前 fetch_usage 不调用控制台 API)

- [ ] **Step 3: 改造 `fetch_usage` 方法**

替换 `src/token_usage/adapters/deepseek.py` 中的 `fetch_usage` 方法。同时需要新增 import：

在文件顶部追加：
```python
import asyncio
from datetime import datetime, timezone
```

（`datetime` 和 `timezone` 已有 import，只需追加 `asyncio`）

替换 `fetch_usage` 方法：

```python
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
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/test_adapters.py -v`
Expected: ALL PASS（包括原有测试和新增测试）

- [ ] **Step 5: Commit**

```bash
git add src/token_usage/adapters/deepseek.py tests/test_adapters.py
git commit -m "feat(deepseek): integrate platform APIs with fallback chain"
```

---

### Task 4: PlatformCard 新增消费面板渲染

**Files:**
- Modify: `src/token_usage/widgets/platform_card.py`

- [ ] **Step 1: 新增 `card-detail` 和 `card-cost` CSS 样式**

在 `PlatformCard.DEFAULT_CSS` 中追加：

```css
    PlatformCard > .card-cost {
        color: $warning;
        margin-bottom: 1;
    }
    PlatformCard > .card-detail {
        color: $text-muted;
        padding-left: 2;
    }
```

- [ ] **Step 2: 修改 `compose` 方法渲染 DeepSeek 消费 extra**

在 `compose` 方法中，`if self.usage.balance:` 块之后、`for quota in self.usage.quotas:` 之前，插入消费面板渲染逻辑：

替换从 `if self.usage.balance:` 到 `for quota` 之前的整个区块为：

```python
        if self.usage.balance:
            yield Static(f"  余额: {self.usage.balance}", classes="card-balance")

        if self.usage.extra:
            if "monthly_cost" in self.usage.extra:
                yield Static(
                    f"  本月消费: {self.usage.extra['monthly_cost']}",
                    classes="card-cost",
                )
            if "monthly_tokens" in self.usage.extra:
                yield Static(
                    f"  本月用量: {self.usage.extra['monthly_tokens']} tokens",
                    classes="card-extra",
                )
            for model in self.usage.extra.get("models", []):
                yield Static(
                    f"    {model['name']}: {model['tokens']} ({model['requests']} req)",
                    classes="card-detail",
                )
            if "available_tokens" in self.usage.extra:
                yield Static(
                    f"  可用: {self.usage.extra['available_tokens']} tokens",
                    classes="card-extra",
                )

        for quota in self.usage.quotas:
```

- [ ] **Step 3: 运行全部测试验证无破坏**

Run: `uv run pytest -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add src/token_usage/widgets/platform_card.py
git commit -m "feat(ui): render DeepSeek consumption panel in PlatformCard"
```

---

### Task 5: 更新 config.example.yaml

**Files:**
- Modify: `config.example.yaml`

- [ ] **Step 1: 添加 `platform_token` 和 `cookie` 配置项**

替换 `config.example.yaml` 中的 deepseek 部分：

```yaml
deepseek:
  api_key: "sk-..."
  base_url: "https://api.deepseek.com"
  # platform_token: "VGnJfZrt..."    # DeepSeek 控制台 session token（从浏览器 DevTools 获取）
  # cookie: "smidV2=...; ..."        # 可选，配合 platform_token 使用
```

- [ ] **Step 2: Commit**

```bash
git add config.example.yaml
git commit -m "docs: add platform_token and cookie config for DeepSeek"
```

---

### Task 6: 运行全量测试和手动验证

**Files:** 无修改

- [ ] **Step 1: 运行全量测试**

Run: `uv run pytest -v`
Expected: ALL PASS

- [ ] **Step 2: 手动运行 TUI 验证（需要配置 platform_token）**

Run: `uv run token-usage`
Expected: DeepSeek 卡片显示余额、月消费、月用量、模型明细（如已配置 platform_token），或仅余额（仅 api_key），或"未配置"
