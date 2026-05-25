from __future__ import annotations

import asyncio
from datetime import datetime, timezone

try:
    from PySide6.QtCore import QObject, Signal, Slot
except ModuleNotFoundError:  # pragma: no cover - fallback for non-GUI test envs
    class QObject:
        def __init__(self, *args, **kwargs):
            super().__init__()

    class _DummySignal:
        def __init__(self, *args, **kwargs):
            self._slots = []

        def connect(self, slot):
            self._slots.append(slot)

        def emit(self, *args, **kwargs):
            for slot in self._slots:
                slot(*args, **kwargs)

    class _SignalDescriptor:
        def __init__(self):
            self._storage_name = ""

        def __set_name__(self, owner, name):
            self._storage_name = f"__dummy_signal_{name}"

        def __get__(self, instance, owner):
            if instance is None:
                return self
            signal = getattr(instance, self._storage_name, None)
            if signal is None:
                signal = _DummySignal()
                setattr(instance, self._storage_name, signal)
            return signal

    def Signal(*args, **kwargs):
        return _SignalDescriptor()

    def Slot(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

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
            continue
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
