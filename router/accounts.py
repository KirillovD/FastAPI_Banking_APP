#this file is for all opetations with accounts

from fastapi import APIRouter, Depends, dependencies
from sqlalchemy.orm import Session
from database import get_db
import models,schemas, utils
from fastapi import HTTPException

from models import Account

router = APIRouter(
    prefix="/accounts",
    tags=["Account Operations"],
    dependencies = [Depends(utils.verify_existing_token)]
)

#to create account we use: created token to extract user id, schemes to input and return info about account,
#session with the database access
@router.post("/", response_model=schemas.AccResponse)
def create_account(account : schemas.AccCreate, user_id : int = Depends(utils.verify_existing_token), db : Session = Depends(get_db)):

    #we check if the user exists in the first place, raise error otherwise
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_account: Account = models.Account(owner_id=user_id, acc_type= account.acc_type,
                                 acc_balance= account.acc_balance)

    db.add(new_account)
    db.commit()
    db.refresh(new_account)

    return new_account

#function to get all user accounts displayed
#again get user id from the token and open the Session
#use list[] in the response model for multiple accounts
@router.get("/", response_model=list[schemas.AccResponse])
def get_all_accounts(user_id : int = Depends(utils.verify_existing_token), db : Session = Depends(get_db)):

    #find all the accounts for the user id from the token
    user_accounts = db.query(models.Account).filter(models.Account.owner == user_id).all()

    return  user_accounts

