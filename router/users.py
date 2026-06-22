from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import exceptions
from crud import users
from database import get_db
import schemas, utils



router = APIRouter(
    prefix="/users",
    tags=["Users Operations"] )

#we use safe response model that does not send password back
@router.post("/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db : Session = Depends(get_db)):

    #we take the input password from user and hash it
    hashed_pwd = utils.hash_password(user.password)

    return users.create_user(user,hashed_pwd,db)



#we use safe response model that does not send password back
#we use curvy braces because user_id is a variable that is entered in the app
@router.get("/", response_model=schemas.UserResponse)
def find_user(user_id: int = Depends(utils.verify_existing_token), db : Session = Depends(get_db)):
    db_user = users.find_user(user_id,db)

    if db_user is None:
        #explain the error if user is not found
        raise exceptions.UserNotFoundException()

    return db_user