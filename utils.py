import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends,HTTPException
from fastapi.security import OAuth2PasswordBearer

secret_key = "Super Secret Key"
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
    token = jwt.encode(payload, secret_key, algorithm="HS256")

    return token


# 1. Настройка "ищейки" токена
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/")

# 2. Сама функция проверки
def verify_existing_token(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        # 3. Декодирование и проверка
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return payload.get("user_id")
    except jwt.ExpiredSignatureError:
        # 4. Ошибка, если время вышло
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        # 5. Ошибка, если токен подделан или сломан
        raise HTTPException(status_code=401, detail="Invalid token")