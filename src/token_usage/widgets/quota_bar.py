from __future__ import annotations

from datetime import datetime, timezone

from rich.text import Text
from textual.widgets import Static

_MAX_BAR_WIDTH = 20


def _to_local(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).astimezone()
    return dt.astimezone()


def format_reset_time(dt: datetime) -> str:
    local = _to_local(dt)
    now = datetime.now(tz=local.tzinfo)
    delta = local - now
    if delta.total_seconds() > 86400 * 30:
        return local.strftime("%m-%d %H:%M")
    if delta.total_seconds() > 86400:
        return local.strftime("%m-%d %H:%M")
    return local.strftime("%H:%M")


class QuotaBar(Static):
    def __init__(self, label: str, used_percent: float, reset_at: datetime | None = None, **kwargs):
        super().__init__(**kwargs)
        self.label = label
        self.used_percent = used_percent
        self.reset_at = reset_at

    def render(self) -> Text:
        filled = int(self.used_percent / 100 * _MAX_BAR_WIDTH)
        filled = max(0, min(filled, _MAX_BAR_WIDTH))
        empty = _MAX_BAR_WIDTH - filled

        bar = "█" * filled + "░" * empty
        color = "green" if self.used_percent < 50 else ("yellow" if self.used_percent < 80 else "red")

        parts = [
            Text(f" {self.label:<10}", style="white"),
            Text(f"[{bar}]", style=color),
            Text(f" {self.used_percent:>3.0f}%", style=color),
        ]

        if self.reset_at:
            reset_str = format_reset_time(self.reset_at)
            parts.append(Text(f"  重置于 {reset_str}", style="dim"))

        return Text.assemble(*parts)
