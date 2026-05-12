import asyncio

import pytest

from tools.api.dealer_store import create_dealer, update_dealer
from tools.api.schemas import DealerCreate, DealerUpdate
from tools.api.services.api_key_service import (
    generate_api_key,
    get_dealer_by_api_key,
    rotate_dealer_api_key,
    verify_api_key,
)
from tools.utils import db


@pytest.fixture()
def api_key_db(tmp_path):
    old_path = db.DB_PATH
    old_backup_done = db._backup_done
    asyncio.run(db.close_pool())
    db.DB_PATH = str(tmp_path / "api_key_service.db")
    db._backup_done = False
    yield
    asyncio.run(db.close_pool())
    db.DB_PATH = old_path
    db._backup_done = old_backup_done


def _create_dealer(email: str, *, active: bool = True):
    dealer, api_key = asyncio.run(
        create_dealer(
            DealerCreate(
                name=email.split("@", 1)[0],
                email=email,
                password="password123",
                plan="trial",
            )
        )
    )
    if not active:
        dealer = asyncio.run(update_dealer(dealer.id, DealerUpdate(active=False)))
    asyncio.run(db.close_pool())
    assert dealer is not None
    return dealer, api_key


def test_generate_api_key_returns_prefixed_secret_and_hash():
    material = generate_api_key()

    assert material.api_key.startswith("agrt_")
    assert material.prefix == material.api_key[:10]
    assert verify_api_key(material.api_key, material.key_hash)
    assert not verify_api_key(material.api_key + "x", material.key_hash)


def test_get_dealer_by_api_key_accepts_existing_dealer_key(api_key_db):
    dealer, api_key = _create_dealer("key-existing@example.com")

    found = asyncio.run(get_dealer_by_api_key(api_key))

    assert found is not None
    assert found.id == dealer.id


def test_rotate_dealer_api_key_invalidates_previous_key(api_key_db):
    dealer, old_api_key = _create_dealer("key-rotate@example.com")

    async def _run():
        rotated = await rotate_dealer_api_key(dealer.id)
        assert rotated is not None
        updated_dealer, material = rotated
        old_lookup = await get_dealer_by_api_key(old_api_key)
        new_lookup = await get_dealer_by_api_key(material.api_key)
        return updated_dealer, material, old_lookup, new_lookup

    updated_dealer, material, old_lookup, new_lookup = asyncio.run(_run())

    assert updated_dealer.id == dealer.id
    assert updated_dealer.api_key_prefix == material.prefix
    assert old_lookup is None
    assert new_lookup is not None
    assert new_lookup.id == dealer.id


def test_rotate_dealer_api_key_rejects_inactive_dealer(api_key_db):
    dealer, _api_key = _create_dealer("key-inactive@example.com", active=False)

    rotated = asyncio.run(rotate_dealer_api_key(dealer.id))

    assert rotated is None
