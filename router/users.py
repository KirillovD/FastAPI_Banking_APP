from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
from dependecies import auth
import exceptions
from crud import users
from database import get_db
import schemas, utils
from dependecies.users import get_current_user

router = APIRouter(
    prefix="/users",
    tags=["Users Operations"] )

#we use safe response model that does not send password back
@router.post("/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate,
                db : Session = Depends(get_db)):

    existing_user = users.get_user_by_email(user.email,db)
    if existing_user:
        raise exceptions.UserAlreadyExists()

    #we take the input password from user and hash it
    hashed_pwd = utils.hash_password(user.password)

    return users.create_user(user,hashed_pwd,db)



#we use safe response model that does not send password back
#we use curvy braces because user_id is a variable that is entered in the app
@router.get("/", response_model=schemas.UserResponse)
def find_user(user : models.User = Depends(get_current_user)):

    return user