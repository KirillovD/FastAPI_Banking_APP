#this file is for all operations with accounts

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import exceptions
from database import get_db
import schemas, utils
from crud import accounts,users


router = APIRouter(
    prefix="/accounts",
    tags=["Account Operations"],
    dependencies = [Depends(utils.verify_existing_token)]
)

#to create account we use: created token to extract user id, schemes to input and return info about account,
#session with the database access
@router.post("/", response_model=schemas.AccResponse)
def create_account(account : schemas.AccCreate, user_id : int = Depends(utils.verify_existing_token), db : Session = Depends(get_db)):


    if not users.find_user(user_id,db):
        raise exceptions.UserNotFoundException()

    return accounts.create_account(account,user_id,db)

@router.get("/", response_model=list[schemas.AccResponse])
def get_all_accounts(user_id : int = Depends(utils.verify_existing_token),
                     db : Session = Depends(get_db)):

    return accounts.get_all_accounts(user_id, db)

