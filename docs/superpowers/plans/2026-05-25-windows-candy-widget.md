# Windows Candy Widget Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Windows-native PySide6 candy-sticker desktop widget that shows token usage while preserving the existing Textual TUI.

**Architecture:** Add a new `token_usage.gui` package. Keep platform fetching shared through existing config, adapter, and model modules. Put deterministic UI mapping logic in pure helpers so most behavior can be tested without launching a Qt window.

**Tech Stack:** Python 3.11+, PySide6, asyncio, existing httpx/PyYAML adapters, pytest.

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `pyproject.toml` | Add `PySide6` dependency and `token-usage-widget` script |
| Create | `src/token_usage/gui/__init__.py` | GUI package marker |
| Create | `src/token_usage/gui/view_models.py` | Pure conversion from `PlatformUsage` to display state and footer alerts |
| Create | `src/token_usage/gui/worker.py` | Qt-compatible background refresh worker and pure async fetch helper |
| Create | `src/token_usage/gui/styles.py` | Candy-sticker QSS and visual constants |
| Create | `src/token_usage/gui/widget_app.py` | PySide6 app entry point, frameless draggable widget, rendering |
| Create | `tests/test_gui_view_models.py` | Unit tests for display state and footer alert selection |
| Create | `tests/test_gui_worker.py` | Unit tests for pure fetch helper result handling |
| Modify | `README.md` | Document widget command, config path, and build command |
| Modify | `AGENTS.md` | Add widget command and Windows GUI notes |

---

### Task 1: Add GUI Display View Models

**Files:**
- Create: `src/token_usage/gui/__init__.py`
- Create: `src/token_usage/gui/view_models.py`
- Create: `tests/test_gui_view_models.py`

- [ ] **Step 1: Write failing tests for platform row mapping and footer messages**

Create `tests/test_gui_view_models.py`:

```python
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from token_usage.gui.view_models import (
    PlatformRowView,
    build_footer_message,
    platform_to_row,
)
from token_usage.models import PlatformUsage, QuotaWindow


def test_platform_to_row_uses_highest_quota_percent():
    usage = PlatformUsage(
        platform="OpenAI",
        status="ok",
        quotas=[
            QuotaWindow(label="5小时限额", used_percent=40),
            QuotaWindow(label="每周限额", used_percent=86, reset_at=datetime.now(tz=timezone.utc) + timedelta(hours=2)),
        ],
    )

    row = platform_to_row(usage)

    assert row == PlatformRowView(
        platform="OpenAI",
        status="ok",
        value="86%",
        detail="每周限额",
        percent=86.0,
        accent="danger",
    )


def test_platform_to_row_uses_balance_when_no_quotas():
    usage = PlatformUsage(
        platform="DeepSeek",
        status="ok",
        balance="¥79.76 CNY",
        extra={"monthly_tokens": "188.9M"},
    )

    row = platform_to_row(usage)

    assert row.platform == "DeepSeek"
    assert row.status == "ok"
    assert row.value == "¥79.76 CNY"
    assert row.detail == "本月 188.9M"
    assert row.percent is None
    assert row.accent == "ok"


def test_platform_to_row_handles_unconfigured():
    usage = PlatformUsage(platform="OpenCode Go", status="unconfigured")

    row = platform_to_row(usage)

    assert row.value == "未配置"
    assert row.detail == "添加配置后开始监控"
    assert row.accent == "muted"


def test_platform_to_row_handles_error_message():
    usage = PlatformUsage(platform="ZhipuAI", status="error", error_msg="401 Unauthorized")

    row = platform_to_row(usage)

    assert row.value == "错误"
    assert row.detail == "401 Unauthorized"
    assert row.accent == "danger"


def test_footer_message_prefers_high_usage_alert():
    usages = [
        PlatformUsage(
            platform="ZhipuAI",
            status="ok",
            quotas=[QuotaWindow(label="5小时", used_percent=91)],
        )
    ]

    assert build_footer_message(usages) == "ZhipuAI 5小时 已使用 91%，注意额度哦"


def test_footer_message_when_all_unconfigured():
    usages = [
        PlatformUsage(platform="OpenAI", status="unconfigured"),
        PlatformUsage(platform="DeepSeek", status="unconfigured"),
    ]

    assert build_footer_message(usages) == "还没有配置平台，先填 config.yaml"


def test_footer_message_when_all_configured_platforms_fail():
    usages = [
        PlatformUsage(platform="OpenAI", status="error", error_msg="timeout"),
        PlatformUsage(platform="DeepSeek", status="error", error_msg="timeout"),
    ]

    assert build_footer_message(usages) == "连接失败，检查网络、代理或 token"


def test_footer_message_normal_state():
    usages = [
        PlatformUsage(
            platform="OpenAI",
            status="ok",
            quotas=[QuotaWindow(label="5小时限额", used_percent=20)],
        )
    ]

    assert build_footer_message(usages) == "状态正常，Token Buddy 正在看着"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest tests/test_gui_view_models.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'token_usage.gui'`.

- [ ] **Step 3: Add the GUI package marker**

Create `src/token_usage/gui/__init__.py`:

```python
"""Windows GUI components for token-usage-viewer."""
```

- [ ] **Step 4: Implement pure view model helpers**

Create `src/token_usage/gui/view_models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from token_usage.models import PlatformUsage, QuotaWindow


@dataclass(frozen=True)
class PlatformRowView:
    platform: str
    status: str
    value: str
    detail: str
    percent: float | None
    accent: str


def platform_to_row(usage: PlatformUsage) -> PlatformRowView:
    if usage.status == "unconfigured":
        return PlatformRowView(
            platform=usage.platform,
            status=usage.status,
            value="未配置",
            detail="添加配置后开始监控",
            percent=None,
            accent="muted",
        )

    if usage.status == "error":
        return PlatformRowView(
            platform=usage.platform,
            status=usage.status,
            value="错误",
            detail=usage.error_msg or "请求失败",
            percent=None,
            accent="danger",
        )

    quota = _highest_quota(usage.quotas)
    if quota:
        return PlatformRowView(
            platform=usage.platform,
            status=usage.status,
            value=f"{quota.used_percent:.0f}%",
            detail=quota.label,
            percent=quota.used_percent,
            accent=_accent_for_percent(quota.used_percent),
        )

    if usage.balance:
        detail = ""
        if usage.extra and usage.extra.get("monthly_tokens"):
            detail = f"本月 {usage.extra['monthly_tokens']}"
        return PlatformRowView(
            platform=usage.platform,
            status=usage.status,
            value=usage.balance,
            detail=detail or "余额正常",
            percent=None,
            accent="ok",
        )

    return PlatformRowView(
        platform=usage.platform,
        status=usage.status,
        value="OK",
        detail="暂无额度窗口",
        percent=None,
        accent="ok",
    )


def build_footer_message(usages: list[PlatformUsage]) -> str:
    for usage in usages:
        if usage.status != "ok":
            continue
        quota = _highest_quota(usage.quotas)
        if quota and quota.used_percent > 80:
            return f"{usage.platform} {quota.label} 已使用 {quota.used_percent:.0f}%，注意额度哦"

    if usages and all(usage.status == "unconfigured" for usage in usages):
        return "还没有配置平台，先填 config.yaml"

    configured = [usage for usage in usages if usage.status != "unconfigured"]
    if configured and all(usage.status == "error" for usage in configured):
        return "连接失败，检查网络、代理或 token"

    return "状态正常，Token Buddy 正在看着"


def _highest_quota(quotas: list[QuotaWindow]) -> QuotaWindow | None:
    if not quotas:
        return None
    return max(quotas, key=lambda quota: quota.used_percent)


def _accent_for_percent(percent: float) -> str:
    if percent > 80:
        return "danger"
    if percent >= 50:
        return "warning"
    return "ok"
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```bash
uv run pytest tests/test_gui_view_models.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/token_usage/gui/__init__.py src/token_usage/gui/view_models.py tests/test_gui_view_models.py
git commit -m "feat: add GUI view models"
```

---

### Task 2: Add Background Fetch Helper and Worker

**Files:**
- Create: `src/token_usage/gui/worker.py`
- Create: `tests/test_gui_worker.py`

- [ ] **Step 1: Write failing tests for the pure async fetch helper**

Create `tests/test_gui_worker.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from token_usage.gui.worker import fetch_all_usage
from token_usage.models import PlatformUsage


class SuccessfulAdapter:
    async def fetch_usage(self) -> PlatformUsage:
        return PlatformUsage(
            platform="OpenAI",
            status="ok",
            updated_at=datetime.now(tz=timezone.utc),
        )


class FailingAdapter:
    async def fetch_usage(self) -> PlatformUsage:
        raise RuntimeError("network down")


@pytest.mark.asyncio
async def test_fetch_all_usage_returns_successes():
    result = await fetch_all_usage([SuccessfulAdapter()])

    assert len(result) == 1
    assert result[0].platform == "OpenAI"
    assert result[0].status == "ok"


@pytest.mark.asyncio
async def test_fetch_all_usage_converts_exceptions_to_error_usage():
    result = await fetch_all_usage([FailingAdapter()])

    assert len(result) == 1
    assert result[0].platform == "Unknown"
    assert result[0].status == "error"
    assert result[0].error_msg == "network down"
    assert result[0].updated_at is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest tests/test_gui_worker.py -q
```

Expected: FAIL with `ModuleNotFoundError` or missing `fetch_all_usage`.

- [ ] **Step 3: Implement worker helper and Qt worker class**

Create `src/token_usage/gui/worker.py`:

```python
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from PySide6.QtCore import QObject, Signal, Slot

from token_usage.adapters.base import BaseAdapter
from token_usage.models import PlatformUsage


async def fetch_all_usage(adapters: list[BaseAdapter]) -> list[PlatformUsage]:
    results = await asyncio.gather(
        *[adapter.fetch_usage() for adapter in adapters],
        return_exceptions=True,
    )

    usages: list[PlatformUsage] = []
    for result in results:
        if isinstance(result, Exception):
            usages.append(
                PlatformUsage(
                    platform="Unknown",
                    status="error",
                    error_msg=str(result),
                    updated_at=datetime.now(tz=timezone.utc),
                )
            )
        else:
            usages.append(result)
    return usages


class RefreshWorker(QObject):
    finished = Signal(list)
    failed = Signal(str)

    def __init__(self, adapters: list[BaseAdapter]):
        super().__init__()
        self.adapters = adapters

    @Slot()
    def run(self) -> None:
        try:
            usages = asyncio.run(fetch_all_usage(self.adapters))
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(usages)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
uv run pytest tests/test_gui_worker.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/token_usage/gui/worker.py tests/test_gui_worker.py
git commit -m "feat: add GUI refresh worker"
```

---

### Task 3: Add PySide6 Dependency, Script Entry, and CLI Parsing

**Files:**
- Modify: `pyproject.toml`
- Create: `src/token_usage/gui/widget_app.py`
- Create: `tests/test_gui_cli.py`

- [ ] **Step 1: Write failing tests for widget CLI argument parsing**

Create `tests/test_gui_cli.py`:

```python
from __future__ import annotations

from token_usage.gui.widget_app import parse_args


def test_parse_args_defaults():
    args = parse_args([])

    assert args.config is None
    assert args.interval is None
    assert args.auto_refresh is True


def test_parse_args_accepts_config_interval_and_no_auto_refresh():
    args = parse_args(["--config", "C:\\token\\config.yaml", "--interval", "60", "--no-auto-refresh"])

    assert args.config == "C:\\token\\config.yaml"
    assert args.interval == 60
    assert args.auto_refresh is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest tests/test_gui_cli.py -q
```

Expected: FAIL with missing `widget_app` or missing `parse_args`.

- [ ] **Step 3: Add PySide6 and script entry**

Modify `pyproject.toml`:

```toml
[project]
dependencies = [
    "textual>=0.50",
    "httpx[socks]",
    "pyyaml",
    "PySide6>=6.7",
]

[project.scripts]
token-usage = "token_usage.__main__:main"
token-usage-widget = "token_usage.gui.widget_app:main"
```

Keep the existing build-system, hatch, and dev dependency sections unchanged.

- [ ] **Step 4: Implement CLI parsing and a minimal placeholder `main`**

Create `src/token_usage/gui/widget_app.py`:

```python
from __future__ import annotations

import argparse
import sys

from PySide6.QtWidgets import QApplication, QLabel


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Token Usage Windows Widget")
    parser.add_argument("--config", help="Path to config.yaml")
    parser.add_argument("--interval", type=int, help="Refresh interval in seconds")
    parser.add_argument(
        "--no-auto-refresh",
        action="store_false",
        dest="auto_refresh",
        help="Disable automatic refresh",
    )
    parser.set_defaults(auto_refresh=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    parse_args(argv)
    app = QApplication(sys.argv[:1])
    label = QLabel("Token Buddy")
    label.resize(240, 120)
    label.show()
    app.exec()
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```bash
uv run pytest tests/test_gui_cli.py -q
```

Expected: PASS.

- [ ] **Step 6: Run dependency sync**

Run:

```bash
uv sync
```

Expected: PySide6 is installed and `uv.lock` updates if needed.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock src/token_usage/gui/widget_app.py tests/test_gui_cli.py
git commit -m "feat: add widget CLI entry"
```

---

### Task 4: Build the Candy-Sticker Widget Window

**Files:**
- Modify: `src/token_usage/gui/widget_app.py`
- Create: `src/token_usage/gui/styles.py`

- [ ] **Step 1: Create candy-sticker QSS constants**

Create `src/token_usage/gui/styles.py`:

```python
from __future__ import annotations

APP_QSS = """
QWidget#shell {
    background: qlineargradient(
        x1: 0, y1: 0,
        x2: 1, y2: 1,
        stop: 0 #fff9ca,
        stop: 0.58 #c7f6ff,
        stop: 1 #ffd6e7
    );
    border-radius: 28px;
}

QLabel#title {
    color: #36506d;
    font-size: 18px;
    font-weight: 800;
}

QLabel#status {
    color: #667085;
    font-size: 12px;
}

QPushButton.iconButton {
    background: rgba(255, 255, 255, 0.64);
    border: 0;
    border-radius: 12px;
    color: #36506d;
    font-size: 14px;
    font-weight: 800;
    min-width: 28px;
    min-height: 28px;
}

QPushButton.iconButton:hover {
    background: rgba(255, 255, 255, 0.88);
}

QFrame.platformRow {
    background: rgba(255, 255, 255, 0.62);
    border: 1px solid rgba(255, 255, 255, 0.72);
    border-radius: 18px;
}

QLabel.platformName {
    color: #334155;
    font-size: 14px;
    font-weight: 800;
}

QLabel.platformDetail {
    color: #667085;
    font-size: 11px;
}

QLabel.platformValue {
    color: #334155;
    font-size: 20px;
    font-weight: 900;
}

QLabel#footer {
    color: #36506d;
    font-size: 12px;
    font-weight: 700;
}
"""

ACCENT_COLORS = {
    "ok": "#74d4aa",
    "warning": "#ffcf5a",
    "danger": "#ff8fb3",
    "muted": "#cbd5e1",
}
```

- [ ] **Step 2: Replace placeholder app with frameless draggable widget**

Replace `src/token_usage/gui/widget_app.py` with:

```python
from __future__ import annotations

import argparse
import sys
from datetime import datetime

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from token_usage.adapters import create_adapters
from token_usage.config import load_config
from token_usage.gui.styles import ACCENT_COLORS, APP_QSS
from token_usage.gui.view_models import PlatformRowView, build_footer_message, platform_to_row
from token_usage.gui.worker import RefreshWorker
from token_usage.models import PlatformUsage


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Token Usage Windows Widget")
    parser.add_argument("--config", help="Path to config.yaml")
    parser.add_argument("--interval", type=int, help="Refresh interval in seconds")
    parser.add_argument(
        "--no-auto-refresh",
        action="store_false",
        dest="auto_refresh",
        help="Disable automatic refresh",
    )
    parser.set_defaults(auto_refresh=True)
    return parser.parse_args(argv)


class PlatformRow(QFrame):
    def __init__(self, row: PlatformRowView):
        super().__init__()
        self.setProperty("class", "platformRow")

        self.name_label = QLabel(row.platform)
        self.name_label.setProperty("class", "platformName")
        self.detail_label = QLabel(row.detail)
        self.detail_label.setProperty("class", "platformDetail")
        self.value_label = QLabel(row.value)
        self.value_label.setProperty("class", "platformValue")
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(9)
        self.progress.setRange(0, 100)

        labels = QVBoxLayout()
        labels.setSpacing(4)
        labels.addWidget(self.name_label)
        labels.addWidget(self.detail_label)

        top = QHBoxLayout()
        top.addLayout(labels, 1)
        top.addWidget(self.value_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)
        layout.addLayout(top)
        layout.addWidget(self.progress)

        self.update_row(row)

    def update_row(self, row: PlatformRowView) -> None:
        self.name_label.setText(row.platform)
        self.detail_label.setText(row.detail)
        self.value_label.setText(row.value)
        color = ACCENT_COLORS[row.accent]
        if row.percent is None:
            self.progress.setValue(0)
            self.progress.setVisible(False)
        else:
            self.progress.setVisible(True)
            self.progress.setValue(int(max(0, min(row.percent, 100))))
        self.progress.setStyleSheet(
            "QProgressBar { background: rgba(255, 255, 255, 0.76); border: 0; border-radius: 4px; }"
            f"QProgressBar::chunk {{ background: {color}; border-radius: 4px; }}"
        )


class TokenBuddyWindow(QMainWindow):
    def __init__(self, config_path: str | None, interval: int | None, auto_refresh: bool):
        super().__init__()
        self.config = load_config(config_path)
        self.adapters = create_adapters(self.config)
        self.interval = interval or int(self.config.get("refresh_interval", 300))
        self.auto_refresh = auto_refresh
        self.rows: dict[str, PlatformRow] = {}
        self._drag_start: QPoint | None = None
        self._worker: RefreshWorker | None = None

        self.setWindowTitle("Token Buddy")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(360, 460)

        shell = QWidget()
        shell.setObjectName("shell")
        self.setCentralWidget(shell)

        self.title_label = QLabel("Token Buddy")
        self.title_label.setObjectName("title")
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("status")
        refresh_button = QPushButton("↻")
        minimize_button = QPushButton("–")
        close_button = QPushButton("×")
        for button in (refresh_button, minimize_button, close_button):
            button.setProperty("class", "iconButton")

        refresh_button.clicked.connect(self.refresh)
        minimize_button.clicked.connect(self.showMinimized)
        close_button.clicked.connect(self.close)

        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        title_stack.addWidget(self.title_label)
        title_stack.addWidget(self.status_label)

        header = QHBoxLayout()
        header.addLayout(title_stack, 1)
        header.addWidget(refresh_button)
        header.addWidget(minimize_button)
        header.addWidget(close_button)

        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(10)

        self.footer_label = QLabel("状态正常，Token Buddy 正在看着")
        self.footer_label.setObjectName("footer")
        self.footer_label.setWordWrap(True)

        layout = QVBoxLayout(shell)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)
        layout.addLayout(header)
        layout.addLayout(self.rows_layout, 1)
        layout.addWidget(self.footer_label)

        self.setStyleSheet(APP_QSS)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        if self.auto_refresh:
            self.timer.start(max(1, self.interval) * 1000)

        self.refresh()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_start and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_start)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_start = None
        event.accept()

    def refresh(self) -> None:
        if self._worker is not None:
            return
        self.status_label.setText("Refreshing...")
        self._worker = RefreshWorker(self.adapters)
        self._worker.finished.connect(self._handle_usages)
        self._worker.failed.connect(self._handle_failure)
        self._worker.run()

    def _handle_usages(self, usages: list[PlatformUsage]) -> None:
        self._worker = None
        self.status_label.setText(f"Updated {datetime.now().strftime('%H:%M:%S')}")
        self.footer_label.setText(build_footer_message(usages))
        for usage in usages:
            row_view = platform_to_row(usage)
            row = self.rows.get(row_view.platform)
            if row is None:
                row = PlatformRow(row_view)
                self.rows[row_view.platform] = row
                self.rows_layout.addWidget(row)
            else:
                row.update_row(row_view)

    def _handle_failure(self, message: str) -> None:
        self._worker = None
        self.status_label.setText("Some services need attention")
        self.footer_label.setText(message)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    app = QApplication(sys.argv[:1])
    window = TokenBuddyWindow(
        config_path=args.config,
        interval=args.interval,
        auto_refresh=args.auto_refresh,
    )
    window.show()
    app.exec()
```

- [ ] **Step 3: Manually launch the widget**

Run:

```bash
uv run token-usage-widget --no-auto-refresh
```

Expected: A frameless `Token Buddy` candy-sticker window appears, can be dragged, and shows platform rows after refresh.

- [ ] **Step 4: Run existing tests**

Run:

```bash
uv run pytest -q
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/token_usage/gui/widget_app.py src/token_usage/gui/styles.py
git commit -m "feat: add candy widget window"
```

---

### Task 5: Make Refresh Truly Non-Blocking

**Files:**
- Modify: `src/token_usage/gui/widget_app.py`
- Modify: `src/token_usage/gui/worker.py`

- [ ] **Step 1: Update `RefreshWorker` usage to run in `QThread`**

Modify `src/token_usage/gui/widget_app.py` imports:

```python
from PySide6.QtCore import QPoint, QThread, Qt, QTimer
```

Modify instance fields in `TokenBuddyWindow.__init__`:

```python
self._thread: QThread | None = None
self._worker: RefreshWorker | None = None
```

Replace `refresh` with:

```python
def refresh(self) -> None:
    if self._worker is not None:
        return
    self.status_label.setText("Refreshing...")
    self._thread = QThread(self)
    self._worker = RefreshWorker(self.adapters)
    self._worker.moveToThread(self._thread)
    self._thread.started.connect(self._worker.run)
    self._worker.finished.connect(self._handle_usages)
    self._worker.failed.connect(self._handle_failure)
    self._worker.finished.connect(self._thread.quit)
    self._worker.failed.connect(self._thread.quit)
    self._thread.finished.connect(self._thread.deleteLater)
    self._thread.start()
```

Modify `_handle_usages` and `_handle_failure` to clear both fields:

```python
def _handle_usages(self, usages: list[PlatformUsage]) -> None:
    self._worker = None
    self._thread = None
    ...

def _handle_failure(self, message: str) -> None:
    self._worker = None
    self._thread = None
    ...
```

- [ ] **Step 2: Run unit tests**

Run:

```bash
uv run pytest tests/test_gui_worker.py tests/test_gui_view_models.py tests/test_gui_cli.py -q
```

Expected: PASS.

- [ ] **Step 3: Manually verify UI responsiveness**

Run:

```bash
uv run token-usage-widget --interval 60
```

Expected:

- Window opens immediately.
- Window can be dragged while a refresh is in progress.
- Refresh button does not start duplicate refreshes.
- Close button exits cleanly.

- [ ] **Step 4: Commit**

```bash
git add src/token_usage/gui/widget_app.py
git commit -m "fix: run widget refresh in background thread"
```

---

### Task 6: Update Documentation and Windows Build Notes

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Update README usage section**

Add this under `## 使用` after the TUI commands:

```markdown
### Windows 桌面小挂件

```powershell
uv run token-usage-widget
uv run token-usage-widget --interval 60
uv run token-usage-widget --config "$env:APPDATA\token-usage\config.yaml"
```

小挂件是 Windows 原生窗口，使用糖果贴纸风格，支持拖动、手动刷新和自动刷新。
```

- [ ] **Step 2: Update README build section**

Add this under the Windows binary command:

```markdown
Windows widget:

```powershell
uv run python -m nuitka --onefile --windows-console-mode=disable --output-dir=dist --output-filename=token-usage-widget.exe src/token_usage/gui/widget_app.py
```
```

- [ ] **Step 3: Update AGENTS commands table**

Add these rows:

```markdown
| Run Windows widget | `uv run token-usage-widget` |
| Build Windows widget binary | `uv run python -m nuitka --onefile --windows-console-mode=disable --output-dir=dist --output-filename=token-usage-widget.exe src/token_usage/gui/widget_app.py` |
```

- [ ] **Step 4: Run final tests**

Run:

```bash
uv run pytest -q
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add README.md AGENTS.md
git commit -m "docs: add Windows widget usage"
```

---

### Task 7: Final Verification and Push

**Files:**
- None unless verification finds issues.

- [ ] **Step 1: Check git status**

Run:

```bash
git status --short --branch
```

Expected: Current branch is `codex/windows-version` and no unexpected uncommitted files exist.

- [ ] **Step 2: Run full tests**

Run:

```bash
uv run pytest -q
```

Expected: All tests pass.

- [ ] **Step 3: Verify CLI help for both commands**

Run:

```bash
uv run token-usage --help
uv run token-usage-widget --help
```

Expected: Both commands show help and exit with status 0.

- [ ] **Step 4: Manually verify widget launch**

Run:

```bash
uv run token-usage-widget --no-auto-refresh
```

Expected: Candy-sticker widget launches, can be dragged, and closes cleanly.

- [ ] **Step 5: Push the branch**

Run:

```bash
git push
```

Expected: Branch `codex/windows-version` pushes to `origin/codex/windows-version`.
