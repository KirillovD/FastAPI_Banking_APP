#this file is for all operations with accounts

from fastapi import APIRouter, Depends

import models
from dependecies import auth
from sqlalchemy.orm import Session
import exceptions
from database import get_db
from crud import accounts as accounts_crud
from dependecies.accounts import get_valid_acc
from dependecies.users import get_current_user
from schemas import accounts

router = APIRouter(
    prefix="/accounts",
    tags=["Account Operations"],
    dependencies = [Depends(auth.verify_existing_token)]
)

#to create account we use: created token to extract user id, schemes to input and return info about account,
#session with the database access
@router.post("/", response_model=accounts.AccResponse)
def create_account(account : accounts.AccCreate,
                   user : models.User = Depends(get_current_user),
                   db : Session = Depends(get_db)):

    new_acc = accounts_crud.create_account(account,user.id,db)
    if not new_acc:
        raise exceptions.IbanGenError
    return new_acc


@router.get("/", response_model=list[accounts.AccResponse])
def get_all_accounts(user : models.User = Depends(get_current_user),
                     db : Session = Depends(get_db)):

    return accounts_crud.get_all_user_accounts(user.id, db)


@router.get("/{acc_id}", response_model=accounts.AccResponse)
def get_acc_by_id(acc_id : int,
                  valid_acc : models.Account = Depends(get_valid_acc)):

    return valid_acc

