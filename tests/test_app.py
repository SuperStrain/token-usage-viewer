import asyncio

import pytest

from token_usage.app import TokenUsageApp
from token_usage.__main__ import main


@pytest.mark.asyncio
async def test_on_mount_watch_mode_starts_refresh_task(monkeypatch):
    app = TokenUsageApp(watch=True, interval=1)

    async def fake_refresh() -> None:
        return None

    monkeypatch.setattr(app, "action_refresh", fake_refresh)

    created = {}

    class DummyTask:
        def cancel(self) -> None:
            return None

    def fake_create_task(coro):
        created["task_created"] = True
        coro.close()
        return DummyTask()

    monkeypatch.setattr(asyncio, "create_task", fake_create_task)

    await app.on_mount()

    assert created.get("task_created") is True
    assert app._refresh_task is not None


def test_app_accepts_config_path(monkeypatch, tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("refresh_interval: 123\n", encoding="utf-8")

    app = TokenUsageApp(config_path=str(config_file))

    assert app.config["refresh_interval"] == 123


def test_cli_passes_config_path_to_app(monkeypatch, tmp_path):
    config_file = tmp_path / "config.yaml"
    created = {}

    class DummyApp:
        def __init__(self, *, watch, interval, config_path):
            created["watch"] = watch
            created["interval"] = interval
            created["config_path"] = config_path

        def run(self):
            created["ran"] = True

    monkeypatch.setattr("sys.argv", ["token-usage", "--config", str(config_file)])
    monkeypatch.setattr("token_usage.__main__.TokenUsageApp", DummyApp)

    main()

    assert created == {
        "watch": False,
        "interval": 300,
        "config_path": str(config_file),
        "ran": True,
    }


def test_cli_help_renders_config_default(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["token-usage", "--help"])

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 0
    help_text = capsys.readouterr().out.replace("\n                       ", "")
    assert "%APPDATA%\\token-usage\\config.yaml" in help_text
