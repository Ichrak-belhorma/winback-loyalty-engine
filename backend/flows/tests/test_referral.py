import pytest
from freezegun import freeze_time

from customers.models import Customer
from flows.tests.conftest import T0
from referrals.models import Referral


@pytest.fixture
def referrer(make_customer):
    return make_customer(first_name="Rita", phone="+15550002222")


def redeem(post, code: str, email: str = "friend@example.com"):
    with freeze_time(T0):
        return post("/api/referrals/redeem", {"code": code, "email": email, "first_name": "Fred"})


def order(post, email: str, n: int):
    with freeze_time(T0):
        return post(
            "/api/webhooks/order-created",
            {"event_id": f"e{n}", "order_id": f"o{n}", "customer_email": email, "total": "30"},
        )


@pytest.mark.django_db
def test_friend_gets_discount_and_referrer_is_rewarded_on_first_order_only(post, referrer):
    response = redeem(post, referrer.referral_code.lower())
    friend = Customer.objects.get(email="friend@example.com")

    assert response.status_code == 201
    assert response.json()["discount_percent"] == 15
    assert friend.enrollments.filter(flow="welcome").exists()

    order(post, friend.email, 1)
    order(post, friend.email, 2)

    referral = Referral.objects.get()
    assert referral.status == "rewarded"
    reward = referrer.messages.get(flow="referral")
    assert reward.step == "referrer_reward"
    assert "15% off" in reward.body


@pytest.mark.django_db
def test_redeem_rejections(post, referrer, make_customer, make_order):
    buyer = make_customer(email="buyer@example.com")
    make_order(buyer, T0)
    redeem(post, referrer.referral_code)

    assert redeem(post, "NOPE2345", "x@example.com").status_code == 404
    assert redeem(post, referrer.referral_code, referrer.email).status_code == 400
    assert redeem(post, referrer.referral_code).status_code == 409  # already referred
    assert redeem(post, referrer.referral_code, buyer.email).status_code == 409
    assert Referral.objects.count() == 1
