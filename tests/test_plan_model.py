import pytest
from pydantic import ValidationError

from tools.api.models.plan import (
    PLAN_LIMITS,
    PlanName,
    get_plan_limits,
    has_remaining_daily_calls,
    normalize_plan,
)
from tools.api.schemas import DealerCreate, DealerOut
from tools.api.schemas.admin import AdminPlanUpdate


def test_plan_limits_define_expected_b2b_tiers():
    assert set(PLAN_LIMITS) == {
        PlanName.FREE,
        PlanName.STARTER,
        PlanName.PRO,
        PlanName.ELITE,
        PlanName.ADMIN,
    }
    assert get_plan_limits("free").daily_limit == 50
    assert get_plan_limits(PlanName.STARTER).daily_limit == 500
    assert get_plan_limits("pro").daily_limit == 2_000
    assert get_plan_limits("elite").daily_limit is None
    assert get_plan_limits("free").roi_max_pct == 10.0
    assert get_plan_limits("starter").roi_max_pct == 15.0
    assert get_plan_limits("pro").roi_max_pct == 30.0
    assert get_plan_limits("elite").roi_max_pct is None
    assert get_plan_limits("admin").alerts_enabled is True


def test_has_remaining_daily_calls_respects_unlimited_plans():
    assert has_remaining_daily_calls("free", 49)
    assert not has_remaining_daily_calls("free", 50)
    assert has_remaining_daily_calls("elite", 50_000)
    assert has_remaining_daily_calls("admin", 50_000)


def test_plan_name_normalization_rejects_unknown_values():
    assert normalize_plan("basic") is PlanName.PRO
    assert normalize_plan("premium") is PlanName.ELITE
    assert normalize_plan("trial") is PlanName.FREE
    with pytest.raises(ValueError):
        normalize_plan("enterprise")


def test_dealer_schemas_use_plan_model():
    created = DealerCreate(
        name="Dealer",
        email="dealer@example.com",
        password="password123",
        plan="starter",
    )
    dealer = DealerOut(
        id=1,
        name=created.name,
        email=created.email,
        plan=created.plan,
        calls_today=7,
    )
    admin_update = AdminPlanUpdate(plan="elite")

    assert created.plan is PlanName.STARTER
    assert dealer.plan_info.daily_limit == 500
    assert dealer.plan_info.roi_max_pct == 15.0
    assert dealer.plan_info.alerts_enabled is True
    assert admin_update.plan is PlanName.ELITE


def test_dealer_schemas_reject_unknown_plan():
    with pytest.raises(ValidationError):
        DealerCreate(
            name="Dealer",
            email="dealer@example.com",
            password="password123",
            plan="enterprise",
        )
