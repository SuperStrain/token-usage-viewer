import argparse
from token_usage.app import TokenUsageApp


def main():
    parser = argparse.ArgumentParser(description="Token Usage Viewer TUI")
    parser.add_argument("--watch", action="store_true", help="Auto-refresh mode")
    parser.add_argument("--interval", type=int, default=300, help="Refresh interval in seconds (default: 300)")
    args = parser.parse_args()
    app = TokenUsageApp(watch=args.watch, interval=args.interval)
    app.run()


if __name__ == "__main__":
    main()
