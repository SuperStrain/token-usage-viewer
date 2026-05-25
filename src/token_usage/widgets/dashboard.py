from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Grid
from textual.widgets import Static

from token_usage.models import PlatformUsage
from token_usage.widgets.platform_card import PlatformCard


class Dashboard(Grid):
    DEFAULT_CSS = """
    Dashboard {
        grid-size: 2 2;
        grid-gutter: 1;
        padding: 1;
        height: 1fr;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cards: dict[str, PlatformCard] = {}

    def compose(self) -> ComposeResult:
        platforms = ["OpenCode Go", "ChatGPT Plus", "DeepSeek", "智谱 AI"]
        for name in platforms:
            card = PlatformCard(PlatformUsage(
                platform=name,
                status="unconfigured",
            ))
            self._cards[name] = card
            yield card

    def update_usage(self, usages: list[PlatformUsage]) -> None:
        for usage in usages:
            card = self._cards.get(usage.platform)
            if card:
                card.update(usage)


class AlertBar(Static):
    DEFAULT_CSS = """
    AlertBar {
        color: yellow;
        padding: 0 2;
        height: auto;
    }
    """

    def __init__(self, **kwargs):
        super().__init__("", **kwargs)

    def update_alerts(self, usages: list[PlatformUsage]) -> None:
        alerts = []
        for usage in usages:
            if usage.status != "ok":
                continue
            for quota in usage.quotas:
                if quota.used_percent > 80:
                    alerts.append(f"⚡ {usage.platform} {quota.label} 即将用完 ({quota.used_percent:.0f}%)")

        self.update("  ".join(alerts) if alerts else "")
