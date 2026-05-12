import asyncio
from types import SimpleNamespace

import pytest

from tools.api.models.plan import PlanName
from tools.api.schemas import DealerOut
from tools.api.services.stripe_client import StripeConfigurationError, StripeSettings
from tools.api.services.stripe_service import StripeBillingService, StripeServiceError


def _dealer(**overrides) -> DealerOut:
    data = {
        "id": 7,
        "name": "Dealer Stripe",
        "email": "stripe@example.com",
        "plan": "trial",
        "active": True,
        "calls_today": 0,
        "stripe_customer_id": None,
    }
    data.update(overrides)
    return DealerOut.model_validate(data)


class FakeDealerStore:
    def __init__(self):
        self.updated: list[tuple[int, str | None]] = []

    async def set_stripe_customer_id(
        self,
        dealer_id: int,
        stripe_customer_id: str | None,
    ) -> DealerOut | None:
        self.updated.append((dealer_id, stripe_customer_id))
        return _dealer(id=dealer_id, stripe_customer_id=stripe_customer_id)


class FakeStripe:
    def __init__(self):
        self.customer_creates: list[dict] = []
        self.checkout_creates: list[dict] = []
        self.portal_creates: list[dict] = []
        self.webhook_calls: list[tuple[bytes | str, str, str]] = []
        fake = self

        class Customer:
            @staticmethod
            def create(**kwargs):
                fake.customer_creates.append(kwargs)
                return {"id": "cus_created"}

        class CheckoutSession:
            @staticmethod
            def create(**kwargs):
                fake.checkout_creates.append(kwargs)
                return {"id": "cs_test", "url": "https://checkout.stripe.test/session"}

        class PortalSession:
            @staticmethod
            def create(**kwargs):
                fake.portal_creates.append(kwargs)
                return {"id": "bps_test", "url": "https://billing.stripe.test/session"}

        class Webhook:
            @staticmethod
            def construct_event(payload, signature, secret):
                fake.webhook_calls.append((payload, signature, secret))
                return {"type": "checkout.session.completed"}

        self.Customer = Customer
        self.checkout = SimpleNamespace(Session=CheckoutSession)
        self.billing_portal = SimpleNamespace(Session=PortalSession)
        self.Webhook = Webhook


@pytest.fixture()
def settings():
    return StripeSettings(
        secret_key="sk_test_service",
        webhook_secret="whsec_test",
        starter_price_id="price_starter",
        pro_price_id="price_pro",
        elite_price_id="price_elite",
        public_url="https://app.example.com",
    )


def test_price_id_for_billable_plans(settings):
    service = StripeBillingService(settings=settings, stripe_api=FakeStripe(), dealers=FakeDealerStore())

    assert service.price_id_for_plan(PlanName.STARTER) == "price_starter"
    assert service.price_id_for_plan("pro") == "price_pro"
    assert service.price_id_for_plan("premium") == "price_elite"
    assert service.plan_from_price_id("price_pro") == PlanName.PRO


def test_price_id_rejects_non_billable_plan(settings):
    service = StripeBillingService(settings=settings, stripe_api=FakeStripe(), dealers=FakeDealerStore())

    with pytest.raises(StripeServiceError, match="free"):
        service.price_id_for_plan("trial")


def test_price_id_requires_configured_env():
    service = StripeBillingService(
        settings=StripeSettings(secret_key="sk_test_service", basic_price_id=None),
        stripe_api=FakeStripe(),
        dealers=FakeDealerStore(),
    )

    with pytest.raises(StripeConfigurationError, match="STRIPE_PRICE_PRO"):
        service.price_id_for_plan("pro")


def test_ensure_customer_creates_and_persists_stripe_customer(settings):
    fake_stripe = FakeStripe()
    fake_store = FakeDealerStore()
    service = StripeBillingService(settings=settings, stripe_api=fake_stripe, dealers=fake_store)

    customer_id = asyncio.run(service.ensure_customer(_dealer()))

    assert customer_id == "cus_created"
    assert fake_store.updated == [(7, "cus_created")]
    assert fake_stripe.customer_creates == [
        {
            "email": "stripe@example.com",
            "name": "Dealer Stripe",
            "metadata": {"dealer_id": "7", "agartha_plan": "free"},
        }
    ]


def test_ensure_customer_reuses_existing_customer(settings):
    fake_stripe = FakeStripe()
    fake_store = FakeDealerStore()
    service = StripeBillingService(settings=settings, stripe_api=fake_stripe, dealers=fake_store)

    customer_id = asyncio.run(service.ensure_customer(_dealer(stripe_customer_id="cus_existing")))

    assert customer_id == "cus_existing"
    assert fake_store.updated == []
    assert fake_stripe.customer_creates == []


def test_create_checkout_session_builds_subscription_payload(settings):
    fake_stripe = FakeStripe()
    service = StripeBillingService(settings=settings, stripe_api=fake_stripe, dealers=FakeDealerStore())

    result = asyncio.run(
        service.create_checkout_session(
            dealer=_dealer(stripe_customer_id="cus_existing"),
            target_plan="elite",
        )
    )

    assert result.id == "cs_test"
    assert result.url == "https://checkout.stripe.test/session"
    assert result.customer_id == "cus_existing"
    assert result.plan == PlanName.ELITE
    assert fake_stripe.checkout_creates == [
        {
            "mode": "subscription",
            "customer": "cus_existing",
            "client_reference_id": "7",
            "line_items": [{"price": "price_elite", "quantity": 1}],
            "success_url": "https://app.example.com/billing/success?session_id={CHECKOUT_SESSION_ID}",
            "cancel_url": "https://app.example.com/billing/cancel",
            "allow_promotion_codes": True,
            "metadata": {"dealer_id": "7", "target_plan": "elite"},
            "subscription_data": {
                "metadata": {"dealer_id": "7", "target_plan": "elite"}
            },
        }
    ]


def test_create_billing_portal_session_uses_customer(settings):
    fake_stripe = FakeStripe()
    service = StripeBillingService(settings=settings, stripe_api=fake_stripe, dealers=FakeDealerStore())

    result = asyncio.run(
        service.create_billing_portal_session(
            dealer=_dealer(stripe_customer_id="cus_existing"),
            return_url="https://app.example.com/account",
        )
    )

    assert result.id == "bps_test"
    assert result.url == "https://billing.stripe.test/session"
    assert result.customer_id == "cus_existing"
    assert fake_stripe.portal_creates == [
        {"customer": "cus_existing", "return_url": "https://app.example.com/account"}
    ]


def test_construct_webhook_event_requires_signature(settings):
    service = StripeBillingService(settings=settings, stripe_api=FakeStripe(), dealers=FakeDealerStore())

    with pytest.raises(StripeServiceError, match="signature"):
        service.construct_webhook_event(b"{}", None)


def test_construct_webhook_event_delegates_to_stripe(settings):
    fake_stripe = FakeStripe()
    service = StripeBillingService(settings=settings, stripe_api=fake_stripe, dealers=FakeDealerStore())

    event = service.construct_webhook_event(b"{}", "sig_test")

    assert event == {"type": "checkout.session.completed"}
    assert fake_stripe.webhook_calls == [(b"{}", "sig_test", "whsec_test")]
