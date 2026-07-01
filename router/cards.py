from typing import Literal

from fastapi import APIRouter, Depends

import models
from dependecies import auth
from sqlalchemy.orm import Session
import exceptions
import utils
from database import get_db
import schemas
from crud import accounts, cards
from dependecies.accounts import get_valid_acc
from dependecies.cards import get_valid_debit_card, get_valid_credit_card
from dependecies.users import get_current_user

router = APIRouter(prefix = "/cards",
                   tags = ["Card Operations"],
                   dependencies = [Depends(auth.verify_existing_token)])


@router.post("/credit", response_model=schemas.CreditCardResponse)
def create_credit_card(card_type_and_pin : schemas.CreateCard,
                       user : models.User = Depends(get_current_user),
                       db : Session = Depends(get_db)):

    return cards.create_credit_card(user.id,card_type_and_pin,db)


@router.post("/debit/{acc_id}", response_model=schemas.DebitCardResponse)
def create_debit_card(acc_id : int,
                      card_type_and_pin : schemas.CreateCard,
                      account : models.Account = Depends(get_valid_acc),
                      db : Session = Depends(get_db)):

    return cards.create_debit_card(account.id, card_type_and_pin, db)


@router.get("/debit/{card_id}", response_model=schemas.DebitCardResponse)
def get_debit_card(card_id : int,
                   valid_card : models.DebitCard = Depends(get_valid_debit_card)):

    return valid_card


@router.get("/credit/{card_id}", response_model=schemas.CreditCardResponse)
def get_credit_card(card_id : int,
                    valid_credit_card : models.CreditCard = Depends(get_valid_credit_card)):

    return valid_credit_card


@router.get("/credit/{card_id}/cvv", response_model=schemas.CardSecretResponse)
def get_credit_card_cvv(card_id : int,
                        valid_credit_card : models.CreditCard = Depends(get_valid_credit_card)):

    return {"cvv": utils.decode_cvv(valid_credit_card.CVV_encrypted)}

@router.get("/debit/{card_id}/cvv", response_model=schemas.CardSecretResponse)
def get_debit_card_cvv(card_id: int,
                        valid_debit_card: models.DebitCard = Depends(get_valid_debit_card)):

    return {"cvv": utils.decode_cvv(valid_debit_card.CVV_encrypted)}
