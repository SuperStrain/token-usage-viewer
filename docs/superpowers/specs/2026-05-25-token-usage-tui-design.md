# Token Usage Viewer TUI - 设计文档

## 概述

一个基于 Python + Textual 的终端 TUI 程序，用于集中查看多个 AI 平台的 Token 用量和额度信息。支持 4 个平台：OpenCode Go、ChatGPT Plus、DeepSeek、智谱 AI。

运行环境：本地 PC Linux。支持单次查询和 `--watch` 持续运行两种模式。

## 架构

### 目录结构

```
token-usage-viewer/
├── pyproject.toml
├── src/
│   └── token_usage/
│       ├── __init__.py
│       ├── __main__.py
│       ├── app.py
│       ├── config.py
│       ├── models.py
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── opencode.py
│       │   ├── openai.py
│       │   ├── deepseek.py
│       │   └── zhipu.py
│       └── widgets/
│           ├── __init__.py
│           ├── dashboard.py
│           ├── platform_card.py
│           └── quota_bar.py
├── config.example.yaml
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-05-25-token-usage-tui-design.md
```

### 设计模式

使用 **Adapter 模式**：每个平台一个适配器，继承统一基类，输出统一数据模型。UI 层不关心数据来源细节。

## 数据模型

### QuotaWindow

表示一个用量限额窗口。

| 字段 | 类型 | 说明 |
|------|------|------|
| `label` | `str` | 窗口名称，如 "滚动(5h)"、"每周"、"每月" |
| `used_percent` | `float` | 已使用百分比 0-100 |
| `reset_at` | `datetime \| None` | 重置时间 |
| `total` | `str \| None` | 总额度，如 "12M tokens"、"¥100" |
| `used` | `str \| None` | 已用额度，如 "1.2M tokens"、"¥36" |

### PlatformUsage

一个平台的完整用量数据。

| 字段 | 类型 | 说明 |
|------|------|------|
| `platform` | `str` | 平台名称 |
| `status` | `str` | "ok" / "error" / "unconfigured" |
| `error_msg` | `str \| None` | 错误信息 |
| `balance` | `str \| None` | 余额（仅 DeepSeek 有） |
| `quotas` | `list[QuotaWindow]` | 限额窗口列表 |
| `extra` | `dict \| None` | 平台特有数据 |
| `updated_at` | `datetime` | 数据更新时间 |

### 抽象基类

```python
class BaseAdapter(ABC):
    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    async def fetch_usage(self) -> PlatformUsage:
        ...
```

## 平台适配器

### OpenCode Go

- **端点**: `GET https://opencode.ai/workspace/{workspace_id}/go`
- **认证**: `Cookie: auth={auth_cookie}`
- **方式**: HTML 页面抓取，正则解析 SolidJS SSR hydration 数据
- **提取字段**: `rollingUsage`、`weeklyUsage`、`monthlyUsage` 的 `usagePercent` 和 `resetInSec`
- **配置项**: `workspace_id`、`auth_cookie`
- **注意**: `auth_cookie` 有效期较长但仍可能过期，过期时 API 返回非预期 HTML，适配器检测到后返回 status=error

### ChatGPT Plus

- **端点**: `GET https://chatgpt.com/backend-api/wham/usage`
- **认证**: `Authorization: Bearer {access_token}`，可选 `ChatGPT-Account-Id: {account_id}`
- **返回**: `rate_limit.primary_window` 中的 `used_percent`、`reset_after_seconds`
- **提取字段**: 5小时限额、每周限额（如有）的百分比和重置时间，计划类型
- **配置项**: `access_token`、`account_id`（可选）
- **注意**: 
  - 非公开内部 API，接口可能变更
  - `access_token` 为短时效 OAuth token（通常数小时），过期时返回 401
  - 获取方式：浏览器登录 ChatGPT → DevTools → Application → Cookies → 复制 `__Secure-next-auth.session-token` 或通过 Network 面板抓取 API 请求中的 Bearer token

### DeepSeek

- **端点**: `GET https://api.deepseek.com/user/balance`
- **认证**: `Authorization: Bearer {api_key}`
- **返回**: `balance_infos` 数组，含 `total_balance`、`granted_balance`、`topped_up_balance`、`currency`
- **提取字段**: 总余额、赠送余额、充值余额、币种
- **配置项**: `api_key`、`base_url`（可选，默认官方）
- **特点**: 仅返回余额，无窗口限额和重置时间

### 智谱 AI

- **端点**: `GET https://open.bigmodel.cn/api/monitor/usage/quota/limit`
- **认证**: `Authorization: Bearer {api_key}`
- **返回**: `data.limits` 数组，每项含 `usage`、`currentValue`、`percentage`、`nextResetTime`（毫秒时间戳）
- **提取字段**:
  - 第一个 `TOKENS_LIMIT`: 5小时限额
  - 第二个 `TOKENS_LIMIT`（新套餐）: 每周限额
  - `TIME_LIMIT`: MCP 工具月限额
  - `data.level`: 套餐等级（lite/pro/max）
- **配置项**: `api_key`、`base_url`（可选，默认国内）

## 配置

配置文件路径: `~/.config/token-usage/config.yaml`

也支持环境变量覆盖（`TOKEN_USAGE_` 前缀）。

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

未配置的平台显示灰色 "未配置" 占位卡片，不会报错。

## TUI 界面

### 布局

2x2 网格仪表盘，4 个平台卡片均匀分布。

```
╭─────────────────────── Token Usage Dashboard ───────────────────────╮
│  按 r 刷新 | 按 q 退出 | 按 1-4 聚焦平台        上次更新: 00:15:30  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─ OpenCode Go ──────────────────────┐  ┌─ 智谱 AI ─────────────┐ │
│  │ 滚动(5h)  [████░░░░░]  33%  2:15   │  │ 5小时   [████████░] 90%│ │
│  │ 每周     [██░░░░░░░]  25%  6d      │  │ 每周    [████░░░░░] 50%│ │
│  │ 每月     [█░░░░░░░░]  12%  27d     │  │ MCP/月  [██░░░░░░░] 21%│ │
│  └────────────────────────────────────┘  └─────────────────────────┘ │
│                                                                     │
│  ┌─ ChatGPT Plus ────────────────────┐  ┌─ DeepSeek ─────────────┐ │
│  │ 5小时限额  [████████░]  85%  1:30  │  │ 余额     ¥79.76 CNY    │ │
│  │ 每周限额   [██░░░░░░░]  20%  5d    │  │ 赠送     ¥10.00        │ │
│  │ 计划: Plus                         │  │ 充值     ¥69.76        │ │
│  └────────────────────────────────────┘  └─────────────────────────┘ │
│                                                                     │
│  ⚡ 智谱 5小时额度即将用完 (90%) | ChatGPT 5小时额度即将用完 (85%)    │
╰─────────────────────────────────────────────────────────────────────╯
```

### 进度条颜色

- `< 50%`: 绿色
- `50% - 80%`: 黄色
- `> 80%`: 红色

### 底部告警栏

任何平台额度 > 80% 时显示黄色警告。

### 键盘操作

| 按键 | 功能 |
|------|------|
| `r` | 手动刷新所有平台数据 |
| `q` | 退出程序 |
| `1-4` | 聚焦对应平台卡片 |

### 运行模式

- **单次查询**: `python -m token_usage`（默认，查询后显示，按 q 退出）
- **持续运行**: `python -m token_usage --watch`（按 `refresh_interval` 自动刷新）
- **刷新间隔**: `--interval 60`（秒，默认 300）

## 错误处理

- 未配置的平台：显示灰色 "未配置" 占位卡片
- API 调用失败：卡片显示红色边框 + 错误信息 + 上次成功数据（如有缓存）
- 网络超时：10 秒超时，显示超时提示
- 所有 API 调用并行执行（`asyncio.gather`），单个平台失败不影响其他平台

## 依赖

- `textual` >= 0.50 — TUI 框架
- `httpx` — 异步 HTTP 客户端（支持 async）
- `pyyaml` — 配置文件解析

构建工具: `uv`，项目通过 `pyproject.toml` 管理。
