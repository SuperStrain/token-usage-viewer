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
