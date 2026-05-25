from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Static

from token_usage.adapters import create_adapters
from token_usage.config import load_config
from token_usage.models import PlatformUsage
from token_usage.widgets.dashboard import AlertBar, Dashboard


class TokenUsageApp(App):
    TITLE = "Token Usage Dashboard"
    CSS = """
    #update-time {
        color: $text-disabled;
        padding: 0 2;
        height: auto;
    }
    """

    BINDINGS = [
        Binding("r", "refresh", "刷新"),
        Binding("q", "quit", "退出"),
        Binding("1", "focus_card(0)", "OpenCode"),
        Binding("2", "focus_card(1)", "OpenAI"),
        Binding("3", "focus_card(2)", "DeepSeek"),
        Binding("4", "focus_card(3)", "ZhipuAI"),
    ]

    def __init__(self, watch: bool = False, interval: int = 300, **kwargs):
        super().__init__(**kwargs)
        self.watch = watch
        self.interval = interval
        self.config = load_config()
        self.adapters = create_adapters(self.config)
        self._refresh_task: asyncio.Task | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Dashboard()
        yield AlertBar()
        yield Static("", id="update-time")
        yield Footer()

    async def on_mount(self) -> None:
        await self.action_refresh()
        if self.watch:
            self._refresh_task = asyncio.create_task(self._auto_refresh_loop())

    async def on_unmount(self) -> None:
        if self._refresh_task:
            self._refresh_task.cancel()

    async def action_refresh(self) -> None:
        results = await asyncio.gather(
            *[adapter.fetch_usage() for adapter in self.adapters],
            return_exceptions=True,
        )

        usages = []
        for result in results:
            if isinstance(result, Exception):
                usages.append(PlatformUsage(
                    platform="Unknown",
                    status="error",
                    error_msg=str(result),
                    updated_at=datetime.now(tz=timezone.utc),
                ))
            else:
                usages.append(result)

        dashboard = self.query_one(Dashboard)
        dashboard.update_usage(usages)

        alert_bar = self.query_one(AlertBar)
        alert_bar.update_alerts(usages)

        now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
        self.query_one("#update-time", Static).update(f"  上次更新: {now}")

    async def _auto_refresh_loop(self) -> None:
        while True:
            await asyncio.sleep(self.interval)
            await self.action_refresh()

    def action_focus_card(self, index: int) -> None:
        cards = list(self.query("PlatformCard"))
        if 0 <= index < len(cards):
            cards[index].focus()
