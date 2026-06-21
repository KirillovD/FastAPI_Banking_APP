from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas
import utils
from fastapi import HTTPException


router = APIRouter(
    prefix="/users",
    tags=["Users Operations"] )


def get_user_by_email(email: str, db: Session):
    return db.query(models.User).filter(models.User.email == email).first()

#we use safe respose model that does not send passwod back
@router.post("/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db : Session = Depends(get_db)):

    #we take the input password from user and hash it
    hashed_pwd = utils.hash_password(user.password)

    #we save all the data and hashed password as User class object
    db_user = models.User(first_name=user.first_name, last_name=user.last_name,
                          email=user.email, password=hashed_pwd)


    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


#we use safe respose model that does not send passwod back
#we use curvy braces because user_id is a variable that is entered in the app
@router.get("/", response_model=schemas.UserResponse)
def find_user(user_id: int = Depends(utils.verify_existing_token), db : Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.user_id == user_id).first()

    if db_user is None:
        #explain the error if user is not found
        raise HTTPException(status_code=404, detail="User not found")

    return db_user