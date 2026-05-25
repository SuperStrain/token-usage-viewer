from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from token_usage.models import PlatformUsage
from token_usage.widgets.quota_bar import QuotaBar

_MAX_BAR_WIDTH = 20


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
                yield Static(self._render_cost_bar(self.usage.extra), classes="card-cost")
            if "monthly_tokens" in self.usage.extra:
                yield Static(
                    f"  本月用量: {self.usage.extra['monthly_tokens']} tokens",
                    classes="card-extra",
                )
            for model_line in self._render_model_bars(self.usage.extra):
                yield Static(model_line, classes="card-detail")
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

    @staticmethod
    def _render_cost_bar(extra: dict) -> Text:
        cost_str = extra["monthly_cost"]
        cost_val = float("".join(c for c in cost_str if c.isdigit() or c == "."))

        balance_str = extra.get("balance_raw", "0")
        balance_val = float(balance_str) if balance_str else 0.0

        total = cost_val + balance_val
        pct = (cost_val / total * 100) if total > 0 else 0

        filled = int(pct / 100 * _MAX_BAR_WIDTH)
        filled = max(0, min(filled, _MAX_BAR_WIDTH))
        empty = _MAX_BAR_WIDTH - filled
        bar = "█" * filled + "░" * empty
        color = "green" if pct < 50 else ("yellow" if pct < 80 else "red")

        return Text.assemble(
            Text(f" 本月消费  ", style="white"),
            Text(f"[{bar}]", style=color),
            Text(f" {pct:>3.0f}%", style=color),
            Text(f"  {cost_str}", style="white"),
        )

    @staticmethod
    def _render_model_bars(extra: dict) -> list[Text]:
        models = extra.get("models", [])
        if not models:
            return []

        def _parse_token_val(s: str) -> float:
            s = s.strip()
            if s.endswith("M"):
                return float(s[:-1]) * 1_000_000
            if s.endswith("K"):
                return float(s[:-1]) * 1_000
            return float(s)

        total_tokens = sum(_parse_token_val(m["tokens"]) for m in models)
        lines = []
        for m in models:
            val = _parse_token_val(m["tokens"])
            pct = (val / total_tokens * 100) if total_tokens > 0 else 0
            filled = int(pct / 100 * _MAX_BAR_WIDTH)
            filled = max(1, min(filled, _MAX_BAR_WIDTH))
            empty = _MAX_BAR_WIDTH - filled
            bar = "█" * filled + "░" * empty
            color = "green" if pct < 50 else ("yellow" if pct < 80 else "red")

            lines.append(Text.assemble(
                Text(f" {m['name']:<10}", style="white"),
                Text(f"[{bar}]", style=color),
                Text(f" {pct:>3.0f}%", style=color),
                Text(f"  {m['tokens']} ({m['requests']} req)", style="dim"),
            ))
        return lines
