from __future__ import annotations

from dataclasses import dataclass

from token_usage.models import PlatformUsage, QuotaWindow


@dataclass(frozen=True)
class PlatformRowView:
    platform: str
    status: str
    value: str
    detail: str
    percent: float | None
    accent: str


def platform_to_row(usage: PlatformUsage) -> PlatformRowView:
    if usage.status == "unconfigured":
        return PlatformRowView(
            platform=usage.platform,
            status=usage.status,
            value="Not configured",
            detail="Add config.yaml to start monitoring",
            percent=None,
            accent="muted",
        )

    if usage.status == "error":
        return PlatformRowView(
            platform=usage.platform,
            status=usage.status,
            value="Error",
            detail=usage.error_msg or "Request failed",
            percent=None,
            accent="danger",
        )

    quota = _highest_quota(usage.quotas)
    if quota is not None:
        return PlatformRowView(
            platform=usage.platform,
            status=usage.status,
            value=f"{quota.used_percent:.0f}%",
            detail=quota.label,
            percent=quota.used_percent,
            accent=_accent_for_percent(quota.used_percent),
        )

    if usage.balance is not None:
        detail = "Balance is healthy"
        if usage.extra and usage.extra.get("monthly_tokens"):
            detail = f"Monthly tokens {usage.extra['monthly_tokens']}"
        return PlatformRowView(
            platform=usage.platform,
            status=usage.status,
            value=usage.balance,
            detail=detail,
            percent=None,
            accent="ok",
        )

    return PlatformRowView(
        platform=usage.platform,
        status=usage.status,
        value="OK",
        detail="No quota window available",
        percent=None,
        accent="ok",
    )


def build_footer_message(usages: list[PlatformUsage]) -> str:
    for usage in usages:
        if usage.status != "ok":
            continue
        quota = _highest_quota(usage.quotas)
        if quota is not None and quota.used_percent > 80:
            return f"{usage.platform} {quota.label} is at {quota.used_percent:.0f}%, watch usage"

    if usages and all(usage.status == "unconfigured" for usage in usages):
        return "No platforms configured yet, update config.yaml"

    configured = [usage for usage in usages if usage.status != "unconfigured"]
    if configured and all(usage.status == "error" for usage in configured):
        return "All configured platforms failed, check network/proxy/token"

    if any(usage.status == "error" for usage in configured):
        return "Some platforms failed, check network/proxy/token"

    return "All clear, Token Buddy is watching"


def _highest_quota(quotas: list[QuotaWindow]) -> QuotaWindow | None:
    if not quotas:
        return None
    return max(quotas, key=lambda quota: quota.used_percent)


def _accent_for_percent(percent: float) -> str:
    if percent > 80:
        return "danger"
    if percent >= 50:
        return "warning"
    return "ok"
