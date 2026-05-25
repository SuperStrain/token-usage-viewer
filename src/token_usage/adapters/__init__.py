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
