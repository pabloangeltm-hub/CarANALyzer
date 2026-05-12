import asyncio

import pytest

from tools.api.schemas import DealerCreate, DealerUpdate
from tools.api.services.dealer_service import DealerService
from tools.utils import db


@pytest.fixture()
def dealer_service_db(tmp_path):
    old_path = db.DB_PATH
    old_backup_done = db._backup_done
    asyncio.run(db.close_pool())
    db.DB_PATH = str(tmp_path / "dealer_service.db")
    db._backup_done = False
    yield
    asyncio.run(db.close_pool())
    db.DB_PATH = old_path
    db._backup_done = old_backup_done


def _create_payload(email: str, *, plan: str = "trial") -> DealerCreate:
    return DealerCreate(
        name=email.split("@", 1)[0],
        email=email,
        password="password123",
        plan=plan,  # type: ignore[arg-type]
    )


def test_dealer_service_creates_and_fetches_dealer(dealer_service_db):
    async def _run():
        service = DealerService()
        created, api_key = await service.create(_create_payload("service@example.com"))
        by_id = await service.get(created.id)
        by_email = await service.get_by_email("SERVICE@example.com")
        return created, api_key, by_id, by_email

    created, api_key, by_id, by_email = asyncio.run(_run())

    assert api_key.startswith("agrt_")
    assert by_id is not None
    assert by_email is not None
    assert by_id.id == created.id
    assert by_email.email == "service@example.com"


def test_dealer_service_lists_and_updates_profile(dealer_service_db):
    async def _run():
        service = DealerService()
        first, _key = await service.create(_create_payload("first@example.com"))
        second, _key = await service.create(_create_payload("second@example.com"))
        updated = await service.update_profile(first.id, DealerUpdate(name="First Dealer"))
        dealers = await service.list(limit=10, offset=0)
        return first, second, updated, dealers

    first, second, updated, dealers = asyncio.run(_run())

    assert updated is not None
    assert updated.id == first.id
    assert updated.name == "First Dealer"
    assert [dealer.id for dealer in dealers] == [second.id, first.id]


def test_dealer_service_updates_plan_active_and_stripe_customer(dealer_service_db):
    async def _run():
        service = DealerService()
        dealer, _key = await service.create(_create_payload("billing@example.com"))
        premium = await service.set_plan(dealer.id, "elite")
        suspended = await service.set_active(dealer.id, False)
        billing = await service.set_stripe_customer_id(dealer.id, "cus_123")
        by_customer = await service.get_by_stripe_customer_id("cus_123")
        return premium, suspended, billing, by_customer

    premium, suspended, billing, by_customer = asyncio.run(_run())

    assert premium is not None
    assert premium.plan == "elite"
    assert suspended is not None
    assert suspended.active is False
    assert billing is not None
    assert billing.stripe_customer_id == "cus_123"
    assert by_customer is not None
    assert by_customer.id == billing.id


def test_dealer_service_tracks_calls_today(dealer_service_db):
    async def _run():
        service = DealerService()
        dealer, _key = await service.create(_create_payload("usage-service@example.com"))
        after_increment = await service.increment_calls_today(dealer.id, amount=3)
        reset_count = await service.reset_calls_today(dealer.id)
        after_reset = await service.get(dealer.id)
        return after_increment, reset_count, after_reset

    after_increment, reset_count, after_reset = asyncio.run(_run())

    assert after_increment is not None
    assert after_increment.calls_today == 3
    assert reset_count == 1
    assert after_reset is not None
    assert after_reset.calls_today == 0


def test_dealer_service_rejects_invalid_call_increment(dealer_service_db):
    async def _run():
        service = DealerService()
        dealer, _key = await service.create(_create_payload("invalid-usage@example.com"))
        with pytest.raises(ValueError, match="amount"):
            await service.increment_calls_today(dealer.id, amount=0)

    asyncio.run(_run())
