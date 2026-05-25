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
