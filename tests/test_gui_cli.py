from __future__ import annotations

from token_usage.gui.widget_app import build_startup_text, parse_args


def test_parse_args_defaults():
    args = parse_args([])

    assert args.config is None
    assert args.interval is None
    assert args.auto_refresh is True


def test_parse_args_accepts_config_interval_and_no_auto_refresh():
    args = parse_args(
        ["--config", "C:\\token\\config.yaml", "--interval", "60", "--no-auto-refresh"]
    )

    assert args.config == "C:\\token\\config.yaml"
    assert args.interval == 60
    assert args.auto_refresh is False


def test_build_startup_text_uses_parsed_args():
    args = parse_args(["--config", "C:\\token\\config.yaml", "--interval", "60"])

    text = build_startup_text(args)

    assert text == "Token Buddy (auto, interval=60, config=C:\\token\\config.yaml)"
