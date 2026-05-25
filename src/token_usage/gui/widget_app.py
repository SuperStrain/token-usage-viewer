from __future__ import annotations

import argparse
import sys
from datetime import datetime
from typing import Any

from token_usage.adapters import create_adapters
from token_usage.config import load_config
from token_usage.gui.styles import ACCENT_COLORS, APP_QSS
from token_usage.gui.view_models import PlatformRowView, build_footer_message, platform_to_row
from token_usage.gui.worker import RefreshWorker
from token_usage.models import PlatformUsage

try:
    from PySide6.QtCore import QPoint, QThread, Qt, QTimer
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

    HAS_PYSIDE = True
except ModuleNotFoundError:  # pragma: no cover - import-safe fallback
    QPoint = Any  # type: ignore[assignment]
    QMouseEvent = Any  # type: ignore[assignment]
    QThread = Any  # type: ignore[assignment]
    Qt = Any  # type: ignore[assignment]
    QTimer = Any  # type: ignore[assignment]
    QApplication = None  # type: ignore[assignment]
    QFrame = object  # type: ignore[assignment]
    QHBoxLayout = Any  # type: ignore[assignment]
    QLabel = Any  # type: ignore[assignment]
    QMainWindow = object  # type: ignore[assignment]
    QProgressBar = Any  # type: ignore[assignment]
    QPushButton = Any  # type: ignore[assignment]
    QVBoxLayout = Any  # type: ignore[assignment]
    QWidget = Any  # type: ignore[assignment]
    HAS_PYSIDE = False

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


def build_startup_text(args: argparse.Namespace) -> str:
    interval = args.interval if args.interval is not None else "default"
    mode = "auto" if args.auto_refresh else "manual"
    config = args.config if args.config else "default-config"
    return f"Token Buddy ({mode}, interval={interval}, config={config})"


class PlatformRow(QFrame):
    def __init__(self, row: PlatformRowView) -> None:
        if not HAS_PYSIDE:
            raise RuntimeError("PySide6 is required to create GUI rows.")
        super().__init__()
        self.setObjectName("platformRow")
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
        color = ACCENT_COLORS.get(row.accent, ACCENT_COLORS["muted"])

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
        if not HAS_PYSIDE:
            raise RuntimeError("PySide6 is required to launch the widget.")
        super().__init__()
        self.config = load_config(config_path)
        self.adapters = create_adapters(self.config)
        self.interval = interval or int(self.config.get("refresh_interval", 300))
        self.auto_refresh = auto_refresh
        self.rows: dict[str, PlatformRow] = {}
        self._drag_start: QPoint | None = None
        self._worker: RefreshWorker | None = None
        self._thread: QThread | None = None

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
        refresh_button = QPushButton("R")
        minimize_button = QPushButton("_")
        close_button = QPushButton("X")
        for button in (refresh_button, minimize_button, close_button):
            button.setProperty("class", "iconButton")
            button.setObjectName("iconButton")

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

        self.footer_label = QLabel("All clear, Token Buddy is watching")
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
        self._thread = QThread(self)
        self._worker = RefreshWorker(self.adapters)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._handle_usages)
        self._worker.failed.connect(self._handle_failure)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.failed.connect(self._worker.deleteLater)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def closeEvent(self, event) -> None:
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(2000)
        super().closeEvent(event)

    def _cleanup_thread(self) -> None:
        self._worker = None
        self._thread = None

    def _handle_usages(self, usages: list[PlatformUsage]) -> None:
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
        self.status_label.setText("Refresh failed")
        self.footer_label.setText(message)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if not HAS_PYSIDE:
        raise RuntimeError("PySide6 is not installed. Install dependencies and retry.")

    app_args = [sys.argv[0], *(argv or [])]
    app = QApplication(app_args)
    window = TokenBuddyWindow(
        config_path=args.config,
        interval=args.interval,
        auto_refresh=args.auto_refresh,
    )
    window.show()
    app.exec()
