from decimal import Decimal

import pytest

import exceptions
import models
import services.credit as credit_services
from enums import AccountType


def _credit_account(
    balance: str,
    *,
    limit: str = "500.00",
    acquired_interest: str = "0.00",
    grace: bool = True,
):
    return models.Account(
        owner_id=1,
        type=AccountType.CREDIT,
        limit=Decimal(limit),
        balance=Decimal(balance),
        acquired_interest=Decimal(acquired_interest),
        grace_period_active=grace,
    )


def test_minimum_payment_uses_fixed_minimum(monkeypatch):
    monkeypatch.setattr(
        credit_services.settings,
        "credit_card_min_payment_amount",
        Decimal("30.00"),
    )
    monkeypatch.setattr(
        credit_services.settings,
        "credit_card_min_payment_percent",
        Decimal("0.03"),
    )

    account = _credit_account("-500.00")

    assert (
        credit_services.calculate_min_credit_account_payment(account)
        == Decimal("30.00")
    )


def test_minimum_payment_uses_percent_when_larger(monkeypatch):
    monkeypatch.setattr(
        credit_services.settings,
        "credit_card_min_payment_amount",
        Decimal("30.00"),
    )
    monkeypatch.setattr(
        credit_services.settings,
        "credit_card_min_payment_percent",
        Decimal("0.03"),
    )

    account = _credit_account("-2000.00", limit="5000.00")

    assert (
        credit_services.calculate_min_credit_account_payment(account)
        == Decimal("60.00")
    )


def test_minimum_payment_never_exceeds_debt(monkeypatch):
    monkeypatch.setattr(
        credit_services.settings,
        "credit_card_min_payment_amount",
        Decimal("30.00"),
    )
    monkeypatch.setattr(
        credit_services.settings,
        "credit_card_min_payment_percent",
        Decimal("0.03"),
    )

    assert (
        credit_services.calculate_minimum_payment_for_debt(
            Decimal("10.00")
        )
        == Decimal("10.00")
    )


def test_daily_interest_uses_apr_derived_rate(monkeypatch):
    monkeypatch.setattr(
        credit_services.settings,
        "credit_card_default_apr",
        Decimal("0.365"),
    )

    account = _credit_account("-3000.00")

    credit_services.calculate_credit_account_acquired_interest(
        account
    )

    assert account.acquired_interest == Decimal("3.00")


def test_daily_interest_accepts_legacy_whole_percent_apr(monkeypatch):
    monkeypatch.setattr(
        credit_services.settings,
        "credit_card_default_apr",
        Decimal("36.5"),
    )

    account = _credit_account("-100.00")

    credit_services.calculate_credit_account_acquired_interest(
        account
    )

    assert account.acquired_interest == Decimal("0.10")


def test_daily_interest_does_not_accrue_without_debt(monkeypatch):
    monkeypatch.setattr(
        credit_services.settings,
        "credit_card_default_apr",
        Decimal("0.20"),
    )

    zero_balance = _credit_account("0.00")
    positive_balance = _credit_account("100.00")

    credit_services.calculate_credit_account_acquired_interest(
        zero_balance
    )
    credit_services.calculate_credit_account_acquired_interest(
        positive_balance
    )

    assert zero_balance.acquired_interest == Decimal("0.00")
    assert positive_balance.acquired_interest == Decimal("0.00")


def test_posting_interest_preserves_original_grace_rule():
    account = _credit_account(
        "-1000.00",
        acquired_interest="500.00",
        grace=False,
    )

    result = credit_services.add_acquired_interest_to_balance(
        account
    )

    assert result.balance == Decimal("-1500.00")
    assert result.acquired_interest == Decimal("0.00")


def test_interest_cannot_be_posted_while_grace_is_active():
    account = _credit_account(
        "-1000.00",
        acquired_interest="500.00",
        grace=True,
    )

    with pytest.raises(exceptions.GraceNoInterest):
        credit_services.add_acquired_interest_to_balance(
            account
        )
