from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import utils
from database import get_db
from crud.users import get_user_by_email
from utils import create_token

from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(
    prefix="/auth",
    tags=["User Authentication"],
)


@router.post("/")
def user_login(
    login_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = get_user_by_email(login_data.username, db)

    if user is None or not utils.verify_password(login_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_token(user.id)
    return {"access_token": token, "token_type": "bearer"}
