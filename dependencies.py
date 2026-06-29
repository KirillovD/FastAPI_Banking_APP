from sqlalchemy.orm import Session
import models,exceptions
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from database import get_db
from utils import secret_key, ALGORITHM
import jwt


# 1. Настройка "ищейки" токена
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/")

# 2. Сама функция проверки
def verify_existing_token(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        # 3. Декодирование и проверка
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        return payload.get("user_id")
    except jwt.ExpiredSignatureError:
        # 4. Ошибка, если время вышло
        raise exceptions.TokenException(detail="Token expired")
    except jwt.InvalidTokenError:
        # 5. Ошибка, если токен подделан или сломан
        raise exceptions.TokenException(detail="Token invalid")



def check_admin(user_id,db : Session=Depends(get_db)):
    return db.query(models.User.is_admin).filter(models.User.id == user_id).scalar()