from datetime import datetime, timezone
from token_usage.models import QuotaWindow, PlatformUsage


def test_quota_window_creation():
    q = QuotaWindow(
        label="滚动(5h)",
        used_percent=33.0,
        reset_at=datetime(2026, 5, 25, 6, 0, tzinfo=timezone.utc),
        total="12M tokens",
        used="4M tokens",
    )
    assert q.label == "滚动(5h)"
    assert q.used_percent == 33.0
    assert q.total == "12M tokens"


def test_quota_window_optional_fields():
    q = QuotaWindow(label="余额", used_percent=0, reset_at=None, total=None, used=None)
    assert q.reset_at is None
    assert q.total is None


def test_platform_usage_ok():
    q = QuotaWindow(label="每周", used_percent=50, reset_at=None, total=None, used=None)
    p = PlatformUsage(
        platform="Test",
        status="ok",
        error_msg=None,
        balance=None,
        quotas=[q],
        extra=None,
        updated_at=datetime.now(tz=timezone.utc),
    )
    assert p.status == "ok"
    assert len(p.quotas) == 1


def test_platform_usage_error():
    p = PlatformUsage(
        platform="Test",
        status="error",
        error_msg="Connection timeout",
        balance=None,
        quotas=[],
        extra=None,
        updated_at=datetime.now(tz=timezone.utc),
    )
    assert p.status == "error"
    assert p.error_msg == "Connection timeout"


def test_platform_usage_unconfigured():
    p = PlatformUsage(
        platform="Test",
        status="unconfigured",
        error_msg=None,
        balance=None,
        quotas=[],
        extra=None,
        updated_at=datetime.now(tz=timezone.utc),
    )
    assert p.status == "unconfigured"
