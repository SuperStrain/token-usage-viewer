# AGENTS.md — token-usage-viewer

## Project
A Textual TUI dashboard showing AI platform token usage across OpenCode, OpenAI, DeepSeek, ZhipuAI.

## Prerequisites
- Python ≥3.11, managed via `uv` (see `uv.lock`)
- Run `uv sync` to install deps before working

## Commands
| Purpose | Command |
|---------|---------|
| Run app | `uv run token-usage` |
| Run app (direct) | `python -m token_usage` |
| Run app on Windows fallback | `powershell -ExecutionPolicy Bypass -File .\run-windows.ps1` |
| Run all tests | `uv run pytest` |
| Run single test file | `uv run pytest tests/test_models.py` |
| Build binary (Nuitka) | `uv run python -m nuitka --onefile --output-dir=dist --output-filename=token-usage src/token_usage/__main__.py` |
| Build Windows binary (Nuitka) | `uv run python -m nuitka --onefile --output-dir=dist --output-filename=token-usage.exe src/token_usage/__main__.py` |

## Architecture
```
src/token_usage/
├── __main__.py    CLI entry (--watch, --interval)
├── app.py          Textual App, CSS, TUI compose + refresh logic
├── config.py       Loads config.yaml → env overrides
├── models.py       PlatformUsage, QuotaWindow dataclasses
├── adapters/       One async adapter per platform (BaseAdapter pattern)
│   ├── base.py
│   ├── opencode.py
│   ├── openai.py
│   ├── deepseek.py
│   └── zhipu.py
└── widgets/
    ├── dashboard.py
    ├── platform_card.py
    └── quota_bar.py
```

## Config
- Default path on Windows: `%APPDATA%\token-usage\config.yaml`
- Default path on Linux/macOS: `~/.config/token-usage/config.yaml`
- Override config path with `--config <path>` or `TOKEN_USAGE_CONFIG`
- Secrets can be injected via env vars (`TOKEN_USAGE_<PLATFORM>_<KEY>`)
- `config.example.yaml` documents all keys

## Adapter rules
- Each adapter inherits `BaseAdapter` and implements `async fetch_usage() → PlatformUsage`
- Adapter receives only its platform's config dict (e.g. `{"api_key": "..."}`)
- When required config keys are missing, return `PlatformUsage(status="unconfigured")`
- Adapters registered in `adapters/__init__.py` `ADAPTERS` dict
