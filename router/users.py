from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
from database import get_db
from dependecies.users import get_current_user
from services import users as user_services
from schemas import users

router = APIRouter(
    prefix="/users",
    tags=["Users Operations"] )

#we use safe response model that does not send password back
@router.post("/", response_model=users.UserResponse)
def create_user(user: users.UserCreate,
                db : Session = Depends(get_db)):

    return user_services.create_user(user,db)



#we use safe response model that does not send password back
#we use curvy braces because user_id is a variable that is entered in the app
@router.get("/", response_model=users.UserResponse)
def find_user(user : models.User = Depends(get_current_user)):

    return user