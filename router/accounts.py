#this file is for all opetations with accounts

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas
from fastapi import HTTPException

from models import Account

router = APIRouter(
    prefix="/accounts",
    tags=["Account Operations"]
)

#to create account we use: user id, schemes to input and return info about account,
#session with the database access
@router.post("/{user_id}", response_model=schemas.AccResponse)
def create_account(user_id : int, account : schemas.AccCreate, db : Session = Depends(get_db)):

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