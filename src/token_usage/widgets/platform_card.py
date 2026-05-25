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
