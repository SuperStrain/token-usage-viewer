# Token Usage Viewer TUI - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python + Textual TUI dashboard that aggregates token usage/quota data from 4 AI platforms (OpenCode Go, ChatGPT Plus, DeepSeek, 智谱 AI).

**Architecture:** Adapter pattern — each platform has a dedicated adapter class inheriting from a shared base. Adapters produce a unified `PlatformUsage` data model. The Textual UI renders a 2x2 grid of platform cards with progress bars, quota info, and reset timers. Async HTTP via httpx for parallel data fetching.

**Tech Stack:** Python 3.11, Textual >= 0.50, httpx, pyyaml, uv (build tool)

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `pyproject.toml` | Project metadata, dependencies, entry point |
| Create | `src/token_usage/__init__.py` | Package init, version |
| Create | `src/token_usage/__main__.py` | CLI entry point (argparse for --watch, --interval) |
| Create | `src/token_usage/models.py` | QuotaWindow, PlatformUsage dataclasses |
| Create | `src/token_usage/config.py` | Load config from YAML + env vars |
| Create | `src/token_usage/adapters/__init__.py` | Adapter registry, create_adapters factory |
| Create | `src/token_usage/adapters/base.py` | BaseAdapter abstract class |
| Create | `src/token_usage/adapters/opencode.py` | OpenCode Go HTML scraper |
| Create | `src/token_usage/adapters/openai.py` | ChatGPT Plus internal API |
| Create | `src/token_usage/adapters/deepseek.py` | DeepSeek balance API |
| Create | `src/token_usage/adapters/zhipu.py` | 智谱 AI quota API |
| Create | `src/token_usage/widgets/__init__.py` | Widgets package |
| Create | `src/token_usage/widgets/quota_bar.py` | Custom progress bar widget (colored by %) |
| Create | `src/token_usage/widgets/platform_card.py` | Single platform card widget |
| Create | `src/token_usage/widgets/dashboard.py` | Main 2x2 grid layout + header + footer |
| Create | `src/token_usage/app.py` | Textual App subclass, key bindings, refresh logic |
| Create | `config.example.yaml` | Example configuration file |
| Create | `tests/__init__.py` | Tests package |
| Create | `tests/test_models.py` | Tests for data models |
| Create | `tests/test_config.py` | Tests for config loading |
| Create | `tests/test_adapters.py` | Tests for all adapters (mocked HTTP) |

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/token_usage/__init__.py`
- Create: `src/token_usage/__main__.py`
- Create: `config.example.yaml`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "token-usage-viewer"
version = "0.1.0"
description = "TUI dashboard for AI platform token usage"
requires-python = ">=3.11"
dependencies = [
    "textual>=0.50",
    "httpx",
    "pyyaml",
]

[project.scripts]
token-usage = "token_usage.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/token_usage"]
```

- [ ] **Step 2: Create src/token_usage/__init__.py**

```python
__version__ = "0.1.0"
```

- [ ] **Step 3: Create src/token_usage/__main__.py**

```python
import argparse
import asyncio
from token_usage.app import TokenUsageApp


def main():
    parser = argparse.ArgumentParser(description="Token Usage Viewer TUI")
    parser.add_argument("--watch", action="store_true", help="Auto-refresh mode")
    parser.add_argument("--interval", type=int, default=300, help="Refresh interval in seconds (default: 300)")
    args = parser.parse_args()
    app = TokenUsageApp(watch=args.watch, interval=args.interval)
    app.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Create config.example.yaml**

```yaml
opencode:
  workspace_id: "wrk_xxx"
  auth_cookie: "Fe26.2**..."

openai:
  access_token: "eyJ..."
  account_id: "acct_xxx"

deepseek:
  api_key: "sk-..."
  base_url: "https://api.deepseek.com"

zhipu:
  api_key: "xxx.yyy"
  base_url: "https://open.bigmodel.cn"

refresh_interval: 300
```

- [ ] **Step 5: Initialize project with uv**

Run: `uv sync`
Expected: Dependencies installed successfully, `token-usage` command available

- [ ] **Step 6: Verify basic import works**

Run: `uv run python -c "from token_usage import __version__; print(__version__)"`
Expected: `0.1.0`

- [ ] **Step 7: Commit**

```bash
git init
git add pyproject.toml src/ config.example.yaml
git commit -m "feat: project scaffolding with pyproject.toml and entry point"
```

---

### Task 2: Data Models

**Files:**
- Create: `src/token_usage/models.py`
- Create: `tests/__init__.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write tests for data models**

```python
# tests/test_models.py
from datetime import datetime, timezone
from token_usage.models import QuotaWindow, PlatformUsage


def test_quota_window_creation():
    q = QuotaWindow(
        label="滚动(5h)",
        used_percent=33.0,
        reset_at=datetime(2026, 5, 25, 6, 0, tzinfo=timezone.utc),
        total="12M tokens",
        used="4M tokens",
    )
    assert q.label == "滚动(5h)"
    assert q.used_percent == 33.0
    assert q.total == "12M tokens"


def test_quota_window_optional_fields():
    q = QuotaWindow(label="余额", used_percent=0, reset_at=None, total=None, used=None)
    assert q.reset_at is None
    assert q.total is None


def test_platform_usage_ok():
    q = QuotaWindow(label="每周", used_percent=50, reset_at=None, total=None, used=None)
    p = PlatformUsage(
        platform="Test",
        status="ok",
        error_msg=None,
        balance=None,
        quotas=[q],
        extra=None,
        updated_at=datetime.now(tz=timezone.utc),
    )
    assert p.status == "ok"
    assert len(p.quotas) == 1


def test_platform_usage_error():
    p = PlatformUsage(
        platform="Test",
        status="error",
        error_msg="Connection timeout",
        balance=None,
        quotas=[],
        extra=None,
        updated_at=datetime.now(tz=timezone.utc),
    )
    assert p.status == "error"
    assert p.error_msg == "Connection timeout"


def test_platform_usage_unconfigured():
    p = PlatformUsage(
        platform="Test",
        status="unconfigured",
        error_msg=None,
        balance=None,
        quotas=[],
        extra=None,
        updated_at=datetime.now(tz=timezone.utc),
    )
    assert p.status == "unconfigured"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'token_usage.models'`

- [ ] **Step 3: Write models.py**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class QuotaWindow:
    label: str
    used_percent: float
    reset_at: datetime | None = None
    total: str | None = None
    used: str | None = None


@dataclass
class PlatformUsage:
    platform: str
    status: str
    error_msg: str | None = None
    balance: str | None = None
    quotas: list[QuotaWindow] = field(default_factory=list)
    extra: dict | None = None
    updated_at: datetime | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_models.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/token_usage/models.py tests/
git commit -m "feat: add QuotaWindow and PlatformUsage data models"
```

---

### Task 3: Config Loader

**Files:**
- Create: `src/token_usage/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write tests for config loader**

```python
# tests/test_config.py
import os
import tempfile
import pytest
from token_usage.config import load_config


def test_load_config_from_yaml():
    yaml_content = """
opencode:
  workspace_id: "wrk_test"
  auth_cookie: "test_cookie"
deepseek:
  api_key: "sk-test"
refresh_interval: 60
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()
        config = load_config(f.name)

    assert config["opencode"]["workspace_id"] == "wrk_test"
    assert config["opencode"]["auth_cookie"] == "test_cookie"
    assert config["deepseek"]["api_key"] == "sk-test"
    assert config["refresh_interval"] == 60
    os.unlink(f.name)


def test_load_config_missing_file():
    config = load_config("/nonexistent/path/config.yaml")
    assert config == {}


def test_load_config_empty_yaml():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("")
        f.flush()
        config = load_config(f.name)

    assert config == {}
    os.unlink(f.name)


def test_load_config_env_override(monkeypatch, tmp_path):
    yaml_content = """
deepseek:
  api_key: "from_yaml"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml_content)

    monkeypatch.setenv("TOKEN_USAGE_OPENAI_API_KEY", "from_env")

    config = load_config(str(config_file))
    assert config["deepseek"]["api_key"] == "from_yaml"
    assert config["openai"]["api_key"] == "from_env"


def test_load_config_partial_platforms():
    yaml_content = """
zhipu:
  api_key: "zhipu_key"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()
        config = load_config(f.name)

    assert "zhipu" in config
    assert "opencode" not in config
    os.unlink(f.name)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write config.py**

```python
from __future__ import annotations

import os
from pathlib import Path

import yaml

_DEFAULT_PATH = Path.home() / ".config" / "token-usage" / "config.yaml"

_ENV_MAP = {
    ("opencode", "workspace_id"): "TOKEN_USAGE_OPENCODE_WORKSPACE_ID",
    ("opencode", "auth_cookie"): "TOKEN_USAGE_OPENCODE_AUTH_COOKIE",
    ("openai", "access_token"): "TOKEN_USAGE_OPENAI_ACCESS_TOKEN",
    ("openai", "account_id"): "TOKEN_USAGE_OPENAI_ACCOUNT_ID",
    ("deepseek", "api_key"): "TOKEN_USAGE_DEEPSEEK_API_KEY",
    ("deepseek", "base_url"): "TOKEN_USAGE_DEEPSEEK_BASE_URL",
    ("zhipu", "api_key"): "TOKEN_USAGE_ZHIPU_API_KEY",
    ("zhipu", "base_url"): "TOKEN_USAGE_ZHIPU_BASE_URL",
}


def load_config(path: str | None = None) -> dict:
    config_path = Path(path) if path else _DEFAULT_PATH
    config: dict = {}
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f)
            if isinstance(data, dict):
                config = data

    if "refresh_interval" not in config:
        config["refresh_interval"] = 300

    for (platform, key), env_var in _ENV_MAP.items():
        value = os.environ.get(env_var)
        if value:
            config.setdefault(platform, {})[key] = value

    return config
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_config.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/token_usage/config.py tests/test_config.py
git commit -m "feat: add config loader with YAML and env var support"
```

---

### Task 4: Base Adapter + Adapter Registry

**Files:**
- Create: `src/token_usage/adapters/__init__.py`
- Create: `src/token_usage/adapters/base.py`

- [ ] **Step 1: Write base adapter**

```python
# src/token_usage/adapters/base.py
from __future__ import annotations

from abc import ABC, abstractmethod

from token_usage.models import PlatformUsage


class BaseAdapter(ABC):
    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    async def fetch_usage(self) -> PlatformUsage:
        ...
```

- [ ] **Step 2: Write adapter registry**

```python
# src/token_usage/adapters/__init__.py
from __future__ import annotations

from token_usage.adapters.base import BaseAdapter
from token_usage.adapters.opencode import OpenCodeAdapter
from token_usage.adapters.openai import OpenAIAdapter
from token_usage.adapters.deepseek import DeepSeekAdapter
from token_usage.adapters.zhipu import ZhipuAdapter

ADAPTERS: dict[str, type[BaseAdapter]] = {
    "opencode": OpenCodeAdapter,
    "openai": OpenAIAdapter,
    "deepseek": DeepSeekAdapter,
    "zhipu": ZhipuAdapter,
}


def create_adapters(config: dict) -> list[BaseAdapter]:
    adapters = []
    for platform_key, adapter_cls in ADAPTERS.items():
        platform_config = config.get(platform_key, {})
        adapters.append(adapter_cls(platform_config))
    return adapters


__all__ = ["BaseAdapter", "ADAPTERS", "create_adapters"]
```

- [ ] **Step 3: Create placeholder adapter files (to avoid import errors)**

Create minimal stubs for each adapter so the registry can import them:

```python
# src/token_usage/adapters/opencode.py
from __future__ import annotations

from datetime import datetime, timezone

from token_usage.adapters.base import BaseAdapter
from token_usage.models import PlatformUsage


class OpenCodeAdapter(BaseAdapter):
    async def fetch_usage(self) -> PlatformUsage:
        return PlatformUsage(
            platform="OpenCode Go",
            status="unconfigured",
            updated_at=datetime.now(tz=timezone.utc),
        )
```

```python
# src/token_usage/adapters/openai.py
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
```

```python
# src/token_usage/adapters/deepseek.py
from __future__ import annotations

from datetime import datetime, timezone

from token_usage.adapters.base import BaseAdapter
from token_usage.models import PlatformUsage


class DeepSeekAdapter(BaseAdapter):
    async def fetch_usage(self) -> PlatformUsage:
        return PlatformUsage(
            platform="DeepSeek",
            status="unconfigured",
            updated_at=datetime.now(tz=timezone.utc),
        )
```

```python
# src/token_usage/adapters/zhipu.py
from __future__ import annotations

from datetime import datetime, timezone

from token_usage.adapters.base import BaseAdapter
from token_usage.models import PlatformUsage


class ZhipuAdapter(BaseAdapter):
    async def fetch_usage(self) -> PlatformUsage:
        return PlatformUsage(
            platform="智谱 AI",
            status="unconfigured",
            updated_at=datetime.now(tz=timezone.utc),
        )
```

- [ ] **Step 4: Verify imports work**

Run: `uv run python -c "from token_usage.adapters import create_adapters; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add src/token_usage/adapters/
git commit -m "feat: add BaseAdapter, adapter registry, and placeholder adapters"
```

---

### Task 5: OpenCode Go Adapter

**Files:**
- Modify: `src/token_usage/adapters/opencode.py`
- Create: `tests/test_adapters.py` (add OpenCode tests)

- [ ] **Step 1: Write tests for OpenCode adapter**

```python
# tests/test_adapters.py
import pytest
from token_usage.adapters.opencode import OpenCodeAdapter
from token_usage.adapters.openai import OpenAIAdapter
from token_usage.adapters.deepseek import DeepSeekAdapter
from token_usage.adapters.zhipu import ZhipuAdapter


def _make_opencode_html(rolling_pct, rolling_sec, weekly_pct, weekly_sec, monthly_pct, monthly_sec):
    return f"""
    <html><script>
    rollingUsage:$R[0]=({{usagePercent:{rolling_pct},resetInSec:{rolling_sec}}});
    weeklyUsage:$R[1]=({{usagePercent:{weekly_pct},resetInSec:{weekly_sec}}});
    monthlyUsage:$R[2]=({{usagePercent:{monthly_pct},resetInSec:{monthly_sec}}});
    </script></html>
    """


@pytest.mark.asyncio
async def test_opencode_parse_success():
    html = _make_opencode_html(33, 7200, 25, 86400, 12, 259200)
    adapter = OpenCodeAdapter({
        "workspace_id": "wrk_test",
        "auth_cookie": "test_cookie",
    })
    result = await adapter._parse_html(html)
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


@pytest.mark.asyncio
async def test_opencode_parse_invalid_html():
    adapter = OpenCodeAdapter({
        "workspace_id": "wrk_test",
        "auth_cookie": "test_cookie",
    })
    result = await adapter._parse_html("<html>no data here</html>")
    assert result.status == "error"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_adapters.py -v -k opencode`
Expected: FAIL — `AttributeError: 'OpenCodeAdapter' object has no attribute '_parse_html'`

- [ ] **Step 3: Implement OpenCode adapter**

```python
# src/token_usage/adapters/opencode.py
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import httpx

from token_usage.adapters.base import BaseAdapter
from token_usage.models import PlatformUsage, QuotaWindow

_PATTERN = re.compile(
    r"(?:rolling|weekly|monthly)Usage:\$R\[\d+\]=\{usagePercent:(\d+),resetInSec:(\d+)\}"
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
```

- [ ] **Step 4: Install pytest-asyncio and run tests**

Run: `uv add --dev pytest-asyncio && uv run pytest tests/test_adapters.py -v -k opencode`
Expected: All 3 OpenCode tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/token_usage/adapters/opencode.py tests/test_adapters.py
git commit -m "feat: implement OpenCode Go adapter with HTML scraping"
```

---

### Task 6: DeepSeek Adapter

**Files:**
- Modify: `src/token_usage/adapters/deepseek.py`
- Modify: `tests/test_adapters.py` (add DeepSeek tests)

- [ ] **Step 1: Add DeepSeek tests to tests/test_adapters.py**

Append to `tests/test_adapters.py`:

```python
@pytest.mark.asyncio
async def test_deepseek_unconfigured():
    adapter = DeepSeekAdapter({})
    result = await adapter.fetch_usage()
    assert result.status == "unconfigured"


@pytest.mark.asyncio
async def test_deepseek_parse_balance():
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
    assert len(result.quotas) == 2
    assert result.quotas[0].label == "赠送余额"
    assert result.quotas[0].used == "¥10.00"
    assert result.quotas[1].label == "充值余额"
    assert result.quotas[1].used == "¥69.76"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_adapters.py -v -k deepseek`
Expected: FAIL — `AttributeError`

- [ ] **Step 3: Implement DeepSeek adapter**

```python
# src/token_usage/adapters/deepseek.py
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from token_usage.adapters.base import BaseAdapter
from token_usage.models import PlatformUsage, QuotaWindow


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
        granted = info.get("granted_balance", "0")
        topped_up = info.get("topped_up_balance", "0")
        symbol = "¥" if currency == "CNY" else "$"

        return PlatformUsage(
            platform="DeepSeek",
            status="ok",
            balance=f"{symbol}{total} {currency}",
            quotas=[
                QuotaWindow(label="赠送余额", used_percent=0, used=f"{symbol}{granted}", reset_at=None),
                QuotaWindow(label="充值余额", used_percent=0, used=f"{symbol}{topped_up}", reset_at=None),
            ],
            updated_at=datetime.now(tz=timezone.utc),
        )
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_adapters.py -v -k deepseek`
Expected: All 2 DeepSeek tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/token_usage/adapters/deepseek.py tests/test_adapters.py
git commit -m "feat: implement DeepSeek balance adapter"
```

---

### Task 7: 智谱 AI Adapter

**Files:**
- Modify: `src/token_usage/adapters/zhipu.py`
- Modify: `tests/test_adapters.py` (add 智谱 tests)

- [ ] **Step 1: Add 智谱 tests to tests/test_adapters.py**

Append to `tests/test_adapters.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_adapters.py -v -k zhipu`
Expected: FAIL — `AttributeError`

- [ ] **Step 3: Implement 智谱 adapter**

```python
# src/token_usage/adapters/zhipu.py
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from token_usage.adapters.base import BaseAdapter
from token_usage.models import PlatformUsage, QuotaWindow

_TOKEN_LABELS = {0: "5小时", 1: "每周"}
_UNIT_LABELS = {3: "小时"}


class ZhipuAdapter(BaseAdapter):
    async def fetch_usage(self) -> PlatformUsage:
        api_key = self.config.get("api_key")
        if not api_key:
            return PlatformUsage(
                platform="智谱 AI",
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
                platform="智谱 AI",
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
            platform="智谱 AI",
            status="ok",
            quotas=quotas,
            extra={"level": level},
            updated_at=datetime.now(tz=timezone.utc),
        )
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_adapters.py -v -k zhipu`
Expected: All 2 智谱 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/token_usage/adapters/zhipu.py tests/test_adapters.py
git commit -m "feat: implement 智谱 AI quota adapter"
```

---

### Task 8: ChatGPT Plus Adapter

**Files:**
- Modify: `src/token_usage/adapters/openai.py`
- Modify: `tests/test_adapters.py` (add OpenAI tests)

- [ ] **Step 1: Add OpenAI tests to tests/test_adapters.py**

Append to `tests/test_adapters.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_adapters.py -v -k openai`
Expected: FAIL — `AttributeError`

- [ ] **Step 3: Implement ChatGPT Plus adapter**

```python
# src/token_usage/adapters/openai.py
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
                platform="ChatGPT Plus",
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
                platform="ChatGPT Plus",
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
            platform="ChatGPT Plus",
            status="ok",
            quotas=quotas,
            extra={"plan": plan},
            updated_at=now,
        )
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_adapters.py -v -k openai`
Expected: All 3 OpenAI tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/token_usage/adapters/openai.py tests/test_adapters.py
git commit -m "feat: implement ChatGPT Plus adapter"
```

---

### Task 9: QuotaBar Widget

**Files:**
- Create: `src/token_usage/widgets/__init__.py`
- Create: `src/token_usage/widgets/quota_bar.py`

- [ ] **Step 1: Create widgets package**

```python
# src/token_usage/widgets/__init__.py
```

(empty file)

- [ ] **Step 2: Implement QuotaBar widget**

```python
# src/token_usage/widgets/quota_bar.py
from __future__ import annotations

from datetime import datetime, timezone

from rich.text import Text
from textual.widgets import Static

_MAX_BAR_WIDTH = 20


class QuotaBar(Static):
    def __init__(self, label: str, used_percent: float, reset_at: datetime | None = None, **kwargs):
        super().__init__(**kwargs)
        self.label = label
        self.used_percent = used_percent
        self.reset_at = reset_at

    def render(self) -> Text:
        filled = int(self.used_percent / 100 * _MAX_BAR_WIDTH)
        filled = max(0, min(filled, _MAX_BAR_WIDTH))
        empty = _MAX_BAR_WIDTH - filled

        bar = "█" * filled + "░" * empty
        color = "green" if self.used_percent < 50 else ("yellow" if self.used_percent < 80 else "red")

        parts = [
            Text(f" {self.label:<10}", style="white"),
            Text(f"[{bar}]", style=color),
            Text(f" {self.used_percent:>3.0f}%", style=color),
        ]

        if self.reset_at:
            delta = self.reset_at - datetime.now(tz=timezone.utc)
            if delta.total_seconds() > 0:
                reset_str = self._format_delta(delta)
                parts.append(Text(f"  {reset_str}", style="dim"))

        return Text.assemble(*parts)

    @staticmethod
    def _format_delta(delta) -> str:
        total_sec = int(delta.total_seconds())
        if total_sec < 3600:
            return f"{total_sec // 60}m"
        elif total_sec < 86400:
            h, m = divmod(total_sec, 3600)
            return f"{h}h{m // 60}m" if m % 60 else f"{h}h"
        else:
            d, rem = divmod(total_sec, 86400)
            h = rem // 3600
            return f"{d}d{h}h" if h else f"{d}d"
```

- [ ] **Step 3: Verify import works**

Run: `uv run python -c "from token_usage.widgets.quota_bar import QuotaBar; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/token_usage/widgets/
git commit -m "feat: add QuotaBar widget with color-coded progress bar"
```

---

### Task 10: PlatformCard Widget

**Files:**
- Create: `src/token_usage/widgets/platform_card.py`

- [ ] **Step 1: Implement PlatformCard widget**

```python
# src/token_usage/widgets/platform_card.py
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from token_usage.models import PlatformUsage
from token_usage.widgets.quota_bar import QuotaBar


class PlatformCard(Vertical):
    DEFAULT_CSS = """
    PlatformCard {
        border: round $primary;
        padding: 1 2;
        margin: 1;
        height: auto;
        max-height: 12;
    }
    PlatformCard.error {
        border: round $error;
    }
    PlatformCard.unconfigured {
        border: round $text-disabled;
    }
    PlatformCard > .card-title {
        text-style: bold;
        margin-bottom: 1;
    }
    PlatformCard > .card-error {
        color: $error;
    }
    PlatformCard > .card-balance {
        color: $accent;
        margin-bottom: 1;
    }
    """

    def __init__(self, usage: PlatformUsage, **kwargs):
        super().__init__(**kwargs)
        self.usage = usage

    def compose(self) -> ComposeResult:
        yield Static(self.usage.platform, classes="card-title")

        if self.usage.status == "unconfigured":
            self.add_class("unconfigured")
            yield Static("  未配置", classes="card-error")
            return

        if self.usage.status == "error":
            self.add_class("error")
            yield Static(f"  错误: {self.usage.error_msg}", classes="card-error")
            return

        if self.usage.balance:
            yield Static(f"  余额: {self.usage.balance}", classes="card-balance")

        for quota in self.usage.quotas:
            yield QuotaBar(
                label=quota.label,
                used_percent=quota.used_percent,
                reset_at=quota.reset_at,
            )

        if self.usage.extra:
            extra_parts = [f"{k}: {v}" for k, v in self.usage.extra.items()]
            yield Static(f"  {' | '.join(extra_parts)}", classes="card-title")

    def update(self, usage: PlatformUsage) -> None:
        self.usage = usage
        self.remove_class("error", "unconfigured")
        self.remove_children()
        for child in self.compose():
            self.mount(child)
```

- [ ] **Step 2: Verify import works**

Run: `uv run python -c "from token_usage.widgets.platform_card import PlatformCard; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/token_usage/widgets/platform_card.py
git commit -m "feat: add PlatformCard widget"
```

---

### Task 11: Dashboard Layout

**Files:**
- Create: `src/token_usage/widgets/dashboard.py`

- [ ] **Step 1: Implement Dashboard widget**

```python
# src/token_usage/widgets/dashboard.py
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Grid
from textual.widgets import Static

from token_usage.models import PlatformUsage
from token_usage.widgets.platform_card import PlatformCard


class Dashboard(Grid):
    DEFAULT_CSS = """
    Dashboard {
        grid-size: 2 2;
        grid-gutter: 1;
        padding: 1;
        height: 1fr;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cards: dict[str, PlatformCard] = {}

    def compose(self) -> ComposeResult:
        platforms = ["OpenCode Go", "ChatGPT Plus", "DeepSeek", "智谱 AI"]
        for name in platforms:
            card = PlatformCard(PlatformUsage(
                platform=name,
                status="unconfigured",
            ))
            self._cards[name] = card
            yield card

    def update_usage(self, usages: list[PlatformUsage]) -> None:
        for usage in usages:
            card = self._cards.get(usage.platform)
            if card:
                card.update(usage)


class AlertBar(Static):
    DEFAULT_CSS = """
    AlertBar {
        color: yellow;
        padding: 0 2;
        height: auto;
    }
    """

    def __init__(self, **kwargs):
        super().__init__("", **kwargs)

    def update_alerts(self, usages: list[PlatformUsage]) -> None:
        alerts = []
        for usage in usages:
            if usage.status != "ok":
                continue
            for quota in usage.quotas:
                if quota.used_percent > 80:
                    alerts.append(f"⚡ {usage.platform} {quota.label} 即将用完 ({quota.used_percent:.0f}%)")

        self.update("  ".join(alerts) if alerts else "")
```

- [ ] **Step 2: Verify import works**

Run: `uv run python -c "from token_usage.widgets.dashboard import Dashboard, AlertBar; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/token_usage/widgets/dashboard.py
git commit -m "feat: add Dashboard grid layout and AlertBar"
```

---

### Task 12: Textual App

**Files:**
- Create: `src/token_usage/app.py`

- [ ] **Step 1: Implement TokenUsageApp**

```python
# src/token_usage/app.py
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Static

from token_usage.adapters import create_adapters
from token_usage.config import load_config
from token_usage.widgets.dashboard import AlertBar, Dashboard


class TokenUsageApp(App):
    TITLE = "Token Usage Dashboard"
    CSS = """
    #update-time {
        color: $text-disabled;
        padding: 0 2;
        height: auto;
    }
    """

    BINDINGS = [
        Binding("r", "refresh", "刷新"),
        Binding("q", "quit", "退出"),
        Binding("1", "focus_card(0)", "OpenCode"),
        Binding("2", "focus_card(1)", "ChatGPT"),
        Binding("3", "focus_card(2)", "DeepSeek"),
        Binding("4", "focus_card(3)", "智谱"),
    ]

    def __init__(self, watch: bool = False, interval: int = 300, **kwargs):
        super().__init__(**kwargs)
        self.watch = watch
        self.interval = interval
        self.config = load_config()
        self.adapters = create_adapters(self.config)
        self._refresh_task: asyncio.Task | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Dashboard()
        yield AlertBar()
        yield Static("", id="update-time")
        yield Footer()

    async def on_mount(self) -> None:
        await self.action_refresh()
        if self.watch:
            self._refresh_task = asyncio.create_task(self._auto_refresh())

    async def on_unmount(self) -> None:
        if self._refresh_task:
            self._refresh_task.cancel()

    async def action_refresh(self) -> None:
        results = await asyncio.gather(
            *[adapter.fetch_usage() for adapter in self.adapters],
            return_exceptions=True,
        )

        usages = []
        for result in results:
            if isinstance(result, Exception):
                from token_usage.models import PlatformUsage
                usages.append(PlatformUsage(
                    platform="Unknown",
                    status="error",
                    error_msg=str(result),
                    updated_at=datetime.now(tz=timezone.utc),
                ))
            else:
                usages.append(result)

        dashboard = self.query_one(Dashboard)
        dashboard.update_usage(usages)

        alert_bar = self.query_one(AlertBar)
        alert_bar.update_alerts(usages)

        now = datetime.now(tz=timezone.utc).strftime("%H:%M:%S")
        self.query_one("#update-time", Static).update(f"  上次更新: {now}")

    async def _auto_refresh(self) -> None:
        while True:
            await asyncio.sleep(self.interval)
            await self.action_refresh()

    def action_focus_card(self, index: int) -> None:
        cards = list(self.query(Dashboard).query("PlatformCard"))
        if 0 <= index < len(cards):
            cards[index].focus()
```

- [ ] **Step 2: Run the app to verify it starts**

Run: `uv run python -m token_usage`
Expected: TUI app launches with 4 "未配置" cards (will need to Ctrl+C to exit)

- [ ] **Step 3: Commit**

```bash
git add src/token_usage/app.py
git commit -m "feat: add Textual App with auto-refresh and key bindings"
```

---

### Task 13: Run All Tests + Final Verification

**Files:**
- None (verification only)

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Verify CLI help**

Run: `uv run python -m token_usage --help`
Expected: Shows argparse help with --watch and --interval options

- [ ] **Step 3: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "chore: final test verification and cleanup"
```
