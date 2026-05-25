from __future__ import annotations

from datetime import datetime, timedelta, timezone

from token_usage.gui.view_models import (
    PlatformRowView,
    build_footer_message,
    platform_to_row,
)
from token_usage.models import PlatformUsage, QuotaWindow


def test_platform_to_row_uses_highest_quota_percent():
    usage = PlatformUsage(
        platform="OpenAI",
        status="ok",
        quotas=[
            QuotaWindow(label="5h", used_percent=40),
            QuotaWindow(
                label="weekly",
                used_percent=86,
                reset_at=datetime.now(tz=timezone.utc) + timedelta(hours=2),
            ),
        ],
    )

    row = platform_to_row(usage)

    assert row == PlatformRowView(
        platform="OpenAI",
        status="ok",
        value="86%",
        detail="weekly",
        percent=86.0,
        accent="danger",
    )


def test_platform_to_row_uses_balance_when_no_quotas():
    usage = PlatformUsage(
        platform="DeepSeek",
        status="ok",
        balance="¥79.76 CNY",
        extra={"monthly_tokens": "188.9M"},
    )

    row = platform_to_row(usage)

    assert row.platform == "DeepSeek"
    assert row.status == "ok"
    assert row.value == "¥79.76 CNY"
    assert row.detail == "Monthly tokens 188.9M"
    assert row.percent is None
    assert row.accent == "ok"


def test_platform_to_row_handles_unconfigured():
    usage = PlatformUsage(platform="OpenCode Go", status="unconfigured")

    row = platform_to_row(usage)

    assert row.value == "Not configured"
    assert row.detail == "Add config.yaml to start monitoring"
    assert row.accent == "muted"


def test_platform_to_row_handles_error_message():
    usage = PlatformUsage(platform="ZhipuAI", status="error", error_msg="401 Unauthorized")

    row = platform_to_row(usage)

    assert row.value == "Error"
    assert row.detail == "401 Unauthorized"
    assert row.accent == "danger"


def test_footer_message_prefers_high_usage_alert():
    usages = [
        PlatformUsage(
            platform="ZhipuAI",
            status="ok",
            quotas=[QuotaWindow(label="5h", used_percent=91)],
        )
    ]

    assert build_footer_message(usages) == "ZhipuAI 5h is at 91%, watch usage"


def test_footer_message_when_all_unconfigured():
    usages = [
        PlatformUsage(platform="OpenAI", status="unconfigured"),
        PlatformUsage(platform="DeepSeek", status="unconfigured"),
    ]

    assert build_footer_message(usages) == "No platforms configured yet, update config.yaml"


def test_footer_message_when_any_configured_platform_fails():
    usages = [
        PlatformUsage(platform="OpenAI", status="error", error_msg="timeout"),
        PlatformUsage(
            platform="DeepSeek",
            status="ok",
            quotas=[QuotaWindow(label="daily", used_percent=10)],
        ),
    ]

    assert build_footer_message(usages) == "Some platforms failed, check network/proxy/token"


def test_footer_message_when_all_configured_platforms_fail():
    usages = [
        PlatformUsage(platform="OpenAI", status="error", error_msg="timeout"),
        PlatformUsage(platform="DeepSeek", status="error", error_msg="timeout"),
    ]

    assert (
        build_footer_message(usages)
        == "All configured platforms failed, check network/proxy/token"
    )


def test_footer_message_normal_state():
    usages = [
        PlatformUsage(
            platform="OpenAI",
            status="ok",
            quotas=[QuotaWindow(label="5h", used_percent=20)],
        )
    ]

    assert build_footer_message(usages) == "All clear, Token Buddy is watching"


def test_platform_to_row_accent_boundaries():
    usage_warning_low = PlatformUsage(
        platform="OpenAI",
        status="ok",
        quotas=[QuotaWindow(label="window", used_percent=50)],
    )
    usage_warning_high = PlatformUsage(
        platform="OpenAI",
        status="ok",
        quotas=[QuotaWindow(label="window", used_percent=80)],
    )
    usage_danger = PlatformUsage(
        platform="OpenAI",
        status="ok",
        quotas=[QuotaWindow(label="window", used_percent=81)],
    )

    assert platform_to_row(usage_warning_low).accent == "warning"
    assert platform_to_row(usage_warning_high).accent == "warning"
    assert platform_to_row(usage_danger).accent == "danger"
