from __future__ import annotations

from datetime import datetime, timezone

import pytest

from token_usage.gui.worker import RefreshWorker, fetch_all_usage
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


def test_refresh_worker_emits_finished(monkeypatch):
    worker = RefreshWorker([SuccessfulAdapter()])
    captured = {}

    def on_finished(usages):
        captured["usages"] = usages

    worker.finished.connect(on_finished)

    async def fake_fetch(_adapters):
        return [
            PlatformUsage(
                platform="OpenAI",
                status="ok",
                updated_at=datetime.now(tz=timezone.utc),
            )
        ]

    monkeypatch.setattr("token_usage.gui.worker.fetch_all_usage", fake_fetch)
    worker.run()

    assert "usages" in captured
    assert captured["usages"][0].platform == "OpenAI"


def test_refresh_worker_emits_failed(monkeypatch):
    worker = RefreshWorker([FailingAdapter()])
    captured = {}

    def on_failed(message):
        captured["message"] = message

    worker.failed.connect(on_failed)

    async def fake_fetch(_adapters):
        raise RuntimeError("boom")

    monkeypatch.setattr("token_usage.gui.worker.fetch_all_usage", fake_fetch)
    worker.run()

    assert captured["message"] == "boom"
