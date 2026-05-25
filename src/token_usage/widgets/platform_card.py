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
        margin: 0 1;
        height: auto;
    }
    PlatformCard.error {
        border: round $error;
    }
    PlatformCard.unconfigured {
        border: round #5f5f5f;
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
    PlatformCard > .card-extra {
        color: $text-muted;
    }
    PlatformCard > .card-cost {
        color: $warning;
        margin-bottom: 1;
    }
    PlatformCard > .card-detail {
        color: $text-muted;
        padding-left: 2;
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
            if "plan" in self.usage.extra:
                yield Static(
                    f"  计划: {self.usage.extra['plan']}",
                    classes="card-extra",
                )
            if "level" in self.usage.extra:
                yield Static(
                    f"  套餐: {self.usage.extra['level']}",
                    classes="card-extra",
                )

        for quota in self.usage.quotas:
            yield QuotaBar(
                label=quota.label,
                used_percent=quota.used_percent,
                reset_at=quota.reset_at,
            )

    def update(self, usage: PlatformUsage) -> None:
        self.usage = usage
        self.remove_class("error", "unconfigured")
        self.remove_children()
        for child in self.compose():
            self.mount(child)
