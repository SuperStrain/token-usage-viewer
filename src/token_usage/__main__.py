import argparse
import sys
from token_usage.app import TokenUsageApp


def _configure_windows_console() -> None:
    if not sys.platform.startswith("win"):
        return

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")


def main():
    _configure_windows_console()
    parser = argparse.ArgumentParser(description="Token Usage Viewer TUI")
    parser.add_argument("--watch", action="store_true", help="Auto-refresh mode")
    parser.add_argument("--interval", type=int, default=300, help="Refresh interval in seconds (default: 300)")
    parser.add_argument(
        "--config",
        help="Path to config.yaml (default: %%APPDATA%%\\token-usage\\config.yaml on Windows)",
    )
    args = parser.parse_args()
    app = TokenUsageApp(watch=args.watch, interval=args.interval, config_path=args.config)
    app.run()


if __name__ == "__main__":
    main()
