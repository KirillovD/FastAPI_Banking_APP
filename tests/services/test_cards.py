from decimal import Decimal

import pytest

import exceptions
import models
from enums import AccountType
from services.cards import calculate_min_credit_account_payment, credit_account_deadline_check, \
    calculate_credit_account_acquired_interest, add_acquired_interest_to_balance


def test_calculate_min_credit_account_payment_with_min_amount():

    fake_account = models.Account(owner_id= 1,
                                  type= AccountType.CREDIT,
                                  limit= Decimal("500.0"),
                                  balance= Decimal("-500.0"))

    result = calculate_min_credit_account_payment(fake_account)

    assert result == Decimal("30.0")


def test_calculate_min_credit_account_payment_with_min_percent():

    fake_account = models.Account(owner_id= 1,
                                  type= AccountType.CREDIT,
                                  limit= Decimal("5000.0"),
                                  balance= Decimal("-2000.0"))

    result = calculate_min_credit_account_payment(fake_account)

    assert result == Decimal("60.0")


def test_credit_account_deadline_check_fail():
    fake_account = models.Account(owner_id= 1,
                                  type= AccountType.CREDIT,
                                  limit= Decimal("5000.0"),
                                  balance= Decimal("-2000.0"))

    result = credit_account_deadline_check(fake_account)

    assert result == False

def test_credit_account_deadline_check_success():
    fake_account = models.Account(owner_id= 1,
                                  type= AccountType.CREDIT,
                                  limit= Decimal("5000.0"),
                                  balance= Decimal("0.0"))

    result = credit_account_deadline_check(fake_account)

    assert result == True


def test_calculate_credit_account_acquired_interest():
    fake_account = models.Account(owner_id= 1,
                                  type= AccountType.CREDIT,
                                  limit= Decimal("5000.0"),
                                  balance= Decimal("-3000.0"),
                                  acquired_interest= Decimal("0.0"))

    result = calculate_credit_account_acquired_interest(fake_account)

    assert result.acquired_interest == Decimal("164.37")


def test_calculate_credit_account_acquired_interest_zero_balance():
    fake_account = models.Account(owner_id= 1,
                                  type= AccountType.CREDIT,
                                  limit= Decimal("5000.0"),
                                  balance= Decimal("0.0"),
                                  acquired_interest= Decimal("0.0"))

    result = calculate_credit_account_acquired_interest(fake_account)

    assert result.acquired_interest == Decimal("0.0")


def test_add_acquired_interest_to_balance_no_grace():
    fake_account = models.Account(owner_id=1,
                                  type= AccountType.CREDIT,
                                  limit= Decimal("5000.0"),
                                  balance= Decimal("-1000.0"),
                                  acquired_interest= Decimal("500.0"),
                                  grace_period_active= False)

    result = add_acquired_interest_to_balance(fake_account)

    assert result.balance == Decimal("-1500.0")


def test_add_acquired_interest_to_balance_grace_active():
    fake_account = models.Account(owner_id=1,
                                  type= AccountType.CREDIT,
                                  limit= Decimal("5000.0"),
                                  balance= Decimal("-1000.0"),
                                  acquired_interest= Decimal("500.0"),
                                  grace_period_active= True)

    with pytest.raises(exceptions.GraceNoInterest) as exc_info:
        add_acquired_interest_to_balance(fake_account)

    assert exc_info.value.status_code == 400