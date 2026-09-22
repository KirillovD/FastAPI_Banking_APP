from sqlalchemy.orm import Session
import exceptions
import models
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from database import get_db
from utils import secret_key, ALGORITHM
import jwt


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/")


def verify_existing_token(token: str = Depends(oauth2_scheme)) -> int:
    try:
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")

        if not isinstance(user_id, int):
            raise exceptions.TokenException(detail="Token identity is missing or invalid")

        return user_id

    except jwt.ExpiredSignatureError:
        raise exceptions.TokenException(detail="Token expired")
    except jwt.InvalidTokenError:
        raise exceptions.TokenException(detail="Token invalid")


def check_admin(
    user_id: int = Depends(verify_existing_token),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        raise exceptions.UserNotFound()

    if not user.is_admin:
        raise exceptions.NotAdmin()

    return user
