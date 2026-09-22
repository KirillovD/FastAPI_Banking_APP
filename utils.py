import random
from datetime import datetime, timedelta, timezone

import bcrypt
import faker.providers.credit_card
import jwt
from cryptography.fernet import Fernet
from dateutil.relativedelta import relativedelta
from faker import Faker
from schwifty import IBAN

from config import settings
from identity import validate_password_bytes


secret_key = settings.secret_key
ALGORITHM = settings.algorithm
encryption_key = settings.encryption_key

faker = Faker()
f = Fernet(encryption_key)


def hash_password(password: str) -> str:
    validate_password_bytes(password)

    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(
        password=pwd_bytes,
        salt=salt,
    )

    return hashed_password.decode("utf-8")


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    try:
        validate_password_bytes(plain_password)
    except ValueError:
        return False

    password_byte_enc = plain_password.encode("utf-8")
    hashed_password_byte_enc = hashed_password.encode("utf-8")

    return bcrypt.checkpw(
        password_byte_enc,
        hashed_password_byte_enc,
    )


def create_token(user_id):
    expire_time = (
        datetime.now(timezone.utc)
        + timedelta(minutes=15)
    )

    payload = {
        "user_id": user_id,
        "exp": expire_time,
    }

    return jwt.encode(
        payload,
        secret_key,
        algorithm=ALGORITHM,
    )


def generate_iban():
    bank_code = "10000000"
    account_num = "".join(
        random.choices(
            "123456789",
            k=10,
        )
    )
    new_iban = IBAN.generate(
        "DE",
        bank_code,
        account_num,
    )

    return str(new_iban)


def generate_card_info(
    card_type,
    pin_code: str,
):
    card_number = faker.credit_card_number(card_type)
    security_code = (
        faker.credit_card_security_code(card_type)
        .encode("utf-8")
    )

    hashed_pin_code = hash_password(str(pin_code))
    encrypted_security_code = f.encrypt(
        security_code
    )

    expiry_date = (
        datetime.now(timezone.utc)
        + relativedelta(years=4)
    )

    return {
        "card_number": card_number,
        "expiry_date": expiry_date,
        "hashed_pin_code": hashed_pin_code,
        "encrypted_security_code": encrypted_security_code,
    }


def decode_cvv(encrypted_cvv) -> str:
    return f.decrypt(encrypted_cvv).decode()
