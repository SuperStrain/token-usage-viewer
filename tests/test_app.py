import asyncio

import pytest

from token_usage.app import TokenUsageApp


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
