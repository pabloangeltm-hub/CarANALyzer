"""Plan names and limits for B2B monetization."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PlanName(StrEnum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ELITE = "elite"
    ADMIN = "admin"
    TRIAL = "trial"
    BASIC = "basic"
    PREMIUM = "premium"


@dataclass(frozen=True)
class PlanLimits:
    plan: PlanName
    daily_limit: int | None
    alerts_enabled: bool
    roi_max_pct: float | None
    history_days: int | None
    api_key_access: bool
    forensic_full: bool
    export_enabled: bool
    poll_interval_minutes: int | None
    description: str


PLAN_LIMITS: dict[PlanName, PlanLimits] = {
    PlanName.FREE: PlanLimits(
        plan=PlanName.FREE,
        daily_limit=50,
        alerts_enabled=False,
        roi_max_pct=10.0,
        history_days=7,
        api_key_access=False,
        forensic_full=False,
        export_enabled=False,
        poll_interval_minutes=24 * 60,
        description="Free: 50 API calls per day and ROI visible up to 10%.",
    ),
    PlanName.STARTER: PlanLimits(
        plan=PlanName.STARTER,
        daily_limit=500,
        alerts_enabled=True,
        roi_max_pct=15.0,
        history_days=30,
        api_key_access=True,
        forensic_full=False,
        export_enabled=False,
        poll_interval_minutes=6 * 60,
        description="Starter: alerts and ROI visible up to 15%.",
    ),
    PlanName.PRO: PlanLimits(
        plan=PlanName.PRO,
        daily_limit=2_000,
        alerts_enabled=True,
        roi_max_pct=30.0,
        history_days=90,
        api_key_access=True,
        forensic_full=True,
        export_enabled=True,
        poll_interval_minutes=60,
        description="Pro: higher quota, exports and ROI visible up to 30%.",
    ),
    PlanName.ELITE: PlanLimits(
        plan=PlanName.ELITE,
        daily_limit=None,
        alerts_enabled=True,
        roi_max_pct=None,
        history_days=None,
        api_key_access=True,
        forensic_full=True,
        export_enabled=True,
        poll_interval_minutes=15,
        description="Elite: unlimited API calls and full ROI visibility.",
    ),
    PlanName.ADMIN: PlanLimits(
        plan=PlanName.ADMIN,
        daily_limit=None,
        alerts_enabled=True,
        roi_max_pct=None,
        history_days=None,
        api_key_access=True,
        forensic_full=True,
        export_enabled=True,
        poll_interval_minutes=None,
        description="Admin: internal unlimited access.",
    ),
}

_LEGACY_PLAN_ALIASES: dict[PlanName, PlanName] = {
    PlanName.TRIAL: PlanName.FREE,
    PlanName.BASIC: PlanName.PRO,
    PlanName.PREMIUM: PlanName.ELITE,
}


def normalize_plan(plan: PlanName | str) -> PlanName:
    parsed = plan if isinstance(plan, PlanName) else PlanName(plan)
    return _LEGACY_PLAN_ALIASES.get(parsed, parsed)


def get_plan_limits(plan: PlanName | str) -> PlanLimits:
    return PLAN_LIMITS[normalize_plan(plan)]


def has_remaining_daily_calls(plan: PlanName | str, calls_today: int) -> bool:
    limit = get_plan_limits(plan).daily_limit
    return limit is None or calls_today < limit
