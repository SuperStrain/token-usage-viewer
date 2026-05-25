# DeepSeek 消费面板设计

## 概述

为 DeepSeek 平台卡片新增消费和用量展示功能。通过 DeepSeek 控制台内部 API 获取月度消费金额、按模型 token 用量等数据，替换原有的纯余额展示。

## 背景

DeepSeek 官方公开 API 仅暴露 `GET /user/balance`（余额查询），无消费历史接口。但 DeepSeek 控制台 (`platform.deepseek.com`) 内部使用两个非公开 API 可以获取完整的消费和用量数据。

## API 接口

### 概览接口

- **URL**: `GET https://platform.deepseek.com/api/v0/users/get_user_summary`
- **认证**: `Authorization: Bearer {platform_token}`
- **额外请求头**: `x-app-version: 1.0.0`
- **可选**: Cookie（`smidV2`, `HWWAFSESTIME`, `HWWAFSESID`）

**响应关键字段：**

| 字段路径 | 类型 | 说明 |
|----------|------|------|
| `biz_data.normal_wallets[].balance` | string | 余额（如 "79.7625591200000000"） |
| `biz_data.normal_wallets[].currency` | string | 币种（"CNY" / "USD"） |
| `biz_data.monthly_costs[].amount` | string | 本月消费金额 |
| `biz_data.monthly_costs[].currency` | string | 消费币种 |
| `biz_data.monthly_token_usage` | string | 本月总 token 用量（如 "188852655"） |
| `biz_data.total_available_token_estimation` | string | 可用 token 估算 |
| `biz_data.current_token` | number | 当前 token 额度 |

### 明细接口

- **URL**: `GET https://platform.deepseek.com/api/v0/usage/amount?month={m}&year={y}`
- **认证**: 同上
- **参数**: `month`（1-12）、`year`（如 2026）

**响应关键字段：**

| 字段路径 | 类型 | 说明 |
|----------|------|------|
| `data.biz_data.total[]` | array | 按模型汇总用量 |
| `total[].model` | string | 模型名（如 "deepseek-v4-pro"） |
| `total[].usage[].type` | string | token 类型 |
| `total[].usage[].amount` | string | 数量 |

**token 类型枚举：**
- `PROMPT_TOKEN` — prompt token（始终为 0，实际用 cache hit + miss 之和）
- `PROMPT_CACHE_HIT_TOKEN` — 缓存命中的 prompt token
- `PROMPT_CACHE_MISS_TOKEN` — 缓存未命中的 prompt token
- `RESPONSE_TOKEN` — 输出 token
- `REQUEST` — 请求数

**月度总 token** = `PROMPT_CACHE_HIT_TOKEN` + `PROMPT_CACHE_MISS_TOKEN` + `RESPONSE_TOKEN`

## 认证方式

使用平台 session token（不是 API key `sk-xxx`）。token 获取方式：登录 `platform.deepseek.com` → DevTools → Network → 找到任意 API 请求的 `Authorization` header 中的 Bearer token。

token 有效期未确认，可能需要定期更新。

## 配置

```yaml
deepseek:
  api_key: "sk-..."                     # 原有，用于 /user/balance 后备
  base_url: "https://api.deepseek.com"  # 原有
  platform_token: "VGnJfZrt..."         # 新增，控制台 session token
  cookie: "smidV2=...; ..."             # 新增，可选
```

**降级策略：**
- 配置了 `platform_token` → 使用控制台 API（双接口），展示完整消费面板
- 仅配置了 `api_key` → 使用原有 `/user/balance`，仅展示余额
- 都未配置 → 显示"未配置"

## 数据流

```
platform_token 配置？
  ├ 是 → 并行调用 get_user_summary + usage/amount
  │      ├ 成功 → 组装 extra dict → 完整消费面板
  │      └ 失败 → 降级到 api_key + /user/balance（如果已配置）
  └ 否 → api_key 配置？
         ├ 是 → 调用 /user/balance → 仅余额
         └ 否 → status="unconfigured"
```

## 数据结构

消费数据通过 `PlatformUsage.extra` 字段传递（无需修改模型）：

```python
extra = {
    "monthly_cost": "¥36.24 CNY",
    "monthly_tokens": "185.3M",
    "models": [
        {"name": "v4-pro", "tokens": "183.6M", "requests": 2483},
        {"name": "v4-flash", "tokens": "3.5M", "requests": 85},
    ],
    "available_tokens": "26.6M",
}
```

**格式化规则：**
- 金额：保留 2 位小数，加币种符号（¥ / $）
- Token 数：>= 1M 用 "X.XM"，>= 1K 用 "X.XK"，否则直接显示

## UI 展示

```
╭─ DeepSeek ──────────────────────────╮
│  余额: ¥79.76 CNY                    │
│  本月消费: ¥36.24 CNY                │
│  本月用量: 185.3M tokens             │
│    v4-pro:    183.6M (2483 req)      │
│    v4-flash:    3.5M (85 req)        │
│  可用: 26.6M tokens                  │
╰──────────────────────────────────────╯
```

**样式：**
- 余额行：`card-balance`（accent 色）
- 消费行：`card-balance`
- 月度用量行：`card-extra`（muted 色）
- 模型明细行：新增 `card-detail`（muted 色，缩进 4 空格）
- 可用行：`card-extra`

**降级（仅 api_key）显示：**
```
╭─ DeepSeek ──────────────────────────╮
│  余额: ¥79.76 CNY                    │
╰──────────────────────────────────────╯
```

## 修改文件清单

| 文件 | 修改内容 |
|------|----------|
| `adapters/deepseek.py` | 新增控制台 API 调用（双接口并行）、数据解析、降级逻辑 |
| `widgets/platform_card.py` | 新增 `card-detail` CSS 样式、渲染 DeepSeek extra 消费数据 |
| `config.example.yaml` | 新增 `platform_token`、`cookie` 配置项及说明 |

不涉及 models.py、其他适配器或核心逻辑的改动。

## 错误处理

- 控制台 API 调用失败（token 过期、网络错误）→ 降级到 `/user/balance` 模式
- 降级也失败 → 显示错误信息
- `usage/amount` 返回空数据 → 不显示模型明细行
- 所有请求共用 httpx.AsyncClient，10 秒超时
