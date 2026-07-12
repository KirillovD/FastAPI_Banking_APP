from unittest.mock import Mock
from urllib import response

import pytest

import exceptions
from services.payments import check_cvv, check_pin_code, is_account_balance_sufficient
from utils import f, faker, hash_password
from tests.conftest import create_user_and_login, create_account


def test_check_cvv():
    cvv = "123".encode("utf-8")
    encrypted_cvv = f.encrypt(cvv)
    assert check_cvv("123",encrypted_cvv)

def test_check_cvv_mising_data():
    cvv = "123".encode("utf-8")
    encrypted_cvv = f.encrypt(cvv)

    with pytest.raises(exceptions.CvvMissing) as exc_info:
        check_cvv("",encrypted_cvv)

    assert exc_info.value.status_code == 400

def test_check_cvv_wrong_input():
    cvv = "123".encode("utf-8")
    encrypted_cvv = f.encrypt(cvv)

    with pytest.raises(exceptions.CvvCodeIncorrect) as exc_info:
        check_cvv("321", encrypted_cvv)

    assert exc_info.value.status_code == 403


def test_check_pin_code():
    input_pin_code = "1234"
    db_hashed_pin = hash_password(input_pin_code)
    assert check_pin_code("1234",db_hashed_pin)

def test_check_pin_code_missing_data():
    input_pin_code = "1234"
    db_hashed_pin = hash_password(input_pin_code)

    with pytest.raises(exceptions.PinMissing) as exc_info:
        check_pin_code("",db_hashed_pin)

    assert exc_info.value.status_code == 400


def test_check_pin_code_wrong_input():
    input_pin_code = "1234"
    db_hashed_pin = hash_password(input_pin_code)

    with pytest.raises(exceptions.PinCodeIncorrect) as exc_info:
         check_pin_code("4321",db_hashed_pin)

    assert exc_info.value.status_code == 403


def test_is_account_balance_sufficient():

    fake_account = Mock(balance=1000.0, overdraft_limit=200.0)
    assert is_account_balance_sufficient(fake_account,500)

def test_is_account_balance_sufficient_wrong():

    fake_account = Mock(balance=1000.0, overdraft_limit=200.0)
    assert not is_account_balance_sufficient(fake_account,2000)