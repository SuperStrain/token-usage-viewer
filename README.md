# token-usage-viewer

AI 平台 Token 用量 TUI 仪表盘，实时查看 OpenCode、OpenAI、DeepSeek、ZhipuAI 的配额使用情况。

## 安装

```bash
uv sync
```

## 配置

创建配置文件（参考 `config.example.yaml`）：

- Windows: `%APPDATA%\token-usage\config.yaml`
- Linux/macOS: `~/.config/token-usage/config.yaml`

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

也可以用 `--config` 指定任意配置文件路径：

```powershell
uv run token-usage --config C:\Users\you\token-usage\config.yaml
```

密钥也可以通过环境变量注入（`TOKEN_USAGE_<PLATFORM>_<KEY>`），例如：

```bash
export TOKEN_USAGE_DEEPSEEK_API_KEY=sk-xxx
```

PowerShell:

```powershell
$env:TOKEN_USAGE_DEEPSEEK_API_KEY = "sk-xxx"
```

## 使用

```bash
# 单次查看
uv run token-usage
# 或直接运行
python -m token_usage

# 自动刷新模式（每 300 秒）
uv run token-usage --watch

# 自定义刷新间隔
uv run token-usage --watch --interval 60
```

Windows 推荐使用 Windows Terminal 或 PowerShell 7 运行，以获得更稳定的 UTF-8 中文显示和 TUI 渲染。

如果当前 Windows 环境没有安装 `uv`，但使用的是本仓库附带的 Ubuntu `.venv` 依赖目录，可以用仓库内的启动脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\run-windows.ps1
```

脚本同样支持 CLI 参数：

```powershell
powershell -ExecutionPolicy Bypass -File .\run-windows.ps1 --watch --interval 60
powershell -ExecutionPolicy Bypass -File .\run-windows.ps1 --config "$env:APPDATA\token-usage\config.yaml"
```

### 快捷键

| 按键 | 功能 |
|------|------|
| `r` | 手动刷新 |
| `q` | 退出 |
| `1` | 聚焦 OpenCode 卡片 |
| `2` | 聚焦 OpenAI 卡片 |
| `3` | 聚焦 DeepSeek 卡片 |
| `4` | 聚焦 ZhipuAI 卡片 |

## 构建二进制

```bash
uv run python -m nuitka --onefile --output-dir=dist --output-filename=token-usage src/token_usage/__main__.py
```

Windows:

```powershell
uv run python -m nuitka --onefile --output-dir=dist --output-filename=token-usage.exe src/token_usage/__main__.py
```

## 技术栈

- [Textual](https://textual.textualize.io/) — TUI 框架
- httpx — HTTP 客户端
- PyYAML — 配置文件解析
