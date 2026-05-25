from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

_CONFIG_ENV_VAR = "TOKEN_USAGE_CONFIG"

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


def default_config_path() -> Path:
    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "token-usage" / "config.yaml"
        return Path.home() / "AppData" / "Roaming" / "token-usage" / "config.yaml"

    home = os.environ.get("HOME")
    if home:
        return Path(home) / ".config" / "token-usage" / "config.yaml"
    return Path.home() / ".config" / "token-usage" / "config.yaml"


def load_config(path: str | os.PathLike[str] | None = None) -> dict:
    config_path = Path(path or os.environ.get(_CONFIG_ENV_VAR) or default_config_path())
    config: dict = {}
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
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
