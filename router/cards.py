from fastapi import APIRouter, Depends
import dependencies
from sqlalchemy.orm import Session
import exceptions
from database import get_db
import schemas
from crud import accounts,users, cards

router = APIRouter(prefix = "/cards",
                   tags = ["Card Operations"],
                   dependencies = [Depends(dependencies.verify_existing_token)])


@router.post("/credit", response_model=schemas.CreditCardResponse)
def create_credit_card(card_type_and_pin : schemas.CreateCard,
                       user_id : int = Depends(dependencies.verify_existing_token),
                       db : Session = Depends(get_db)):

    return cards.create_credit_card(user_id,card_type_and_pin,db)


@router.post("/debit/{acc_id}", response_model=schemas.DebitCardResponse)
def create_debit_card(card_type_and_pin: schemas.CreateCard,
                      acc_id: int ,
                      user_id : int = Depends(dependencies.verify_existing_token),
                      db: Session = Depends(get_db)):

    account = accounts.get_acc_by_id(acc_id,db)
    if not account:
        raise exceptions.AccountNotFoundException()

    if not account.owner_id == user_id:
        raise exceptions.NotYourAccountException

    return cards.create_debit_card(acc_id, card_type_and_pin, db)