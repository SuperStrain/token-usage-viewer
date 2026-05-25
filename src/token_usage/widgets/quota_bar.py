from __future__ import annotations

from datetime import datetime, timezone

from rich.text import Text
from textual.widgets import Static

_MAX_BAR_WIDTH = 20


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
            delta = self.reset_at - datetime.now(tz=timezone.utc)
            if delta.total_seconds() > 0:
                reset_str = self._format_delta(delta)
                parts.append(Text(f"  {reset_str}", style="dim"))

        return Text.assemble(*parts)

    @staticmethod
    def _format_delta(delta) -> str:
        total_sec = int(delta.total_seconds())
        if total_sec < 3600:
            return f"{total_sec // 60}m"
        elif total_sec < 86400:
            h, m = divmod(total_sec, 3600)
            return f"{h}h{m // 60}m" if m % 60 else f"{h}h"
        else:
            d, rem = divmod(total_sec, 86400)
            h = rem // 3600
            return f"{d}d{h}h" if h else f"{d}d"
