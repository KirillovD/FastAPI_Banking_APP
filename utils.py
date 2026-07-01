import bcrypt
import faker.providers.credit_card
import jwt
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
import exceptions
from config import settings
import random
from schwifty import IBAN
from faker import Faker
from cryptography.fernet import Fernet

secret_key = settings.secret_key
ALGORITHM = settings.algorithm
encryption_key = settings.encryption_key

faker = Faker()
f = Fernet(encryption_key)


def hash_password(password: str) -> str:
    #convert into bytes
    pwd_bytes = password.encode('utf-8')

    #creating the salt
    salt = bcrypt.gensalt()

    #hashing the pass
    hashed_password = bcrypt.hashpw(password=pwd_bytes, salt=salt)

    # returned after decoding
    return hashed_password.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    #convert them both into bytes
    password_byte_enc = plain_password.encode('utf-8')
    hashed_password_byte_enc = hashed_password.encode('utf-8')

    # compare
    return bcrypt.checkpw(password_byte_enc, hashed_password_byte_enc)

#function creates token for every user when they log in
#it will be used as a 15 min vip pass for them to access the database
def create_token(user_id):

    #set timer for 15 min
    expire_time = datetime.now(timezone.utc)+timedelta(minutes=15)

    #using payload to also put the exp info in the token
    payload = { "user_id" : user_id,
                "exp" : expire_time}

    #create token with user id, our own unique secret key using this algo
    token = jwt.encode(payload, secret_key, algorithm=ALGORITHM)

    return token

def generate_iban():
    bank_code = "10000000"
    account_num = "".join(random.choices("123456789", k=10))
    try:
        new_iban = IBAN.generate("DE",bank_code,account_num)
    except ValueError:
        raise

    return str(new_iban)


def generate_card_info(card_type, pin_code: int):

    card_number = faker.credit_card_number(card_type)
    security_code = faker.credit_card_security_code(card_type).encode("utf-8")

    hashed_pin_code = hash_password(str(pin_code))
    encrypted_security_code = f.encrypt(security_code)

    future_date = datetime.now() + relativedelta(years=4)

    # 2. Делаем этот объект timezone-aware (добавляем UTC)
    expiry_dt_tz = future_date.replace(tzinfo=timezone.utc)

    return {"card_number": card_number,
            "expiry_date" : expiry_dt_tz,
            "hashed_pin_code" : hashed_pin_code,
            "encrypted_security_code" : encrypted_security_code}

def decode_cvv(encrypted_cvv):

    return f.decrypt(encrypted_cvv.encode()).decode()