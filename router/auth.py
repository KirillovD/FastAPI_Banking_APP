from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError
from sqlalchemy.orm import Session

import utils
from crud.users import get_user_by_email
from database import get_db
from identity import canonicalize_email, password_fits_bcrypt
from utils import create_token


router = APIRouter(
    prefix="/auth",
    tags=["User Authentication"],
)


@router.post("/")
def user_login(
    login_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    try:
        email = canonicalize_email(login_data.username)
    except ValidationError:
        email = None

    if (
        email is None
        or not password_fits_bcrypt(login_data.password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user = get_user_by_email(email, db)

    if (
        user is None
        or not utils.verify_password(
            login_data.password,
            user.password,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_token(user.id)
    return {
        "access_token": token,
        "token_type": "bearer",
    }
