from __future__ import annotations

import argparse
import sys


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


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    from PySide6.QtWidgets import QApplication, QLabel

    app_args = [sys.argv[0], *(argv or [])]
    app = QApplication(app_args)
    label = QLabel(build_startup_text(args))
    label.resize(240, 120)
    label.show()
    app.exec()
