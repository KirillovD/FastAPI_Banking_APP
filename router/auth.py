#this file has all the endpoint functions when it comes to authentication of users

from fastapi import APIRouter, Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session

import exceptions
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
def user_login(login_data : OAuth2PasswordRequestForm = Depends(), db : Session = Depends(get_db)):

    user = get_user_by_email(login_data.username, db)
    if user is None:
        raise exceptions.UserNotFound(detail="User with this email is not registered")

    if not utils.verify_password(login_data.password, user.password):
        raise HTTPException(status_code=401, detail="Wrong password")

    token = create_token(user.id)
    return {"access_token": token, "token_type": "bearer"}



