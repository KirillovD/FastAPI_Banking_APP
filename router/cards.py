from fastapi import APIRouter, Depends

import models
from dependecies import auth
from sqlalchemy.orm import Session
import utils
from database import get_db
from crud import cards as cards_crud
from dependecies.accounts import get_valid_acc
from dependecies.cards import get_valid_card
from dependecies.users import get_current_user
from schemas import cards
from services import cards as card_services

router = APIRouter(prefix = "/cards",
                   tags = ["Card Operations"],
                   dependencies = [Depends(auth.verify_existing_token)])


@router.post("/credit", response_model=cards.CardResponse)
def create_credit_card(card_type_and_pin : cards.CreateCard,
                       user : models.User = Depends(get_current_user),
                       db : Session = Depends(get_db)):

    return card_services.create_credit_card(card_type_and_pin,user,db)



@router.post("/debit/{acc_id}", response_model=cards.CardResponse)
def create_debit_card(acc_id : int,
                      card_type_and_pin : cards.CreateCard,
                      account : models.Account = Depends(get_valid_acc),
                      db : Session = Depends(get_db)):

    return card_services.create_debit_card(card_type_and_pin,account, db)


@router.get("/{card_id}", response_model=cards.CardResponse)
def get_card(card_id : int,
             valid_card : models.Card = Depends(get_valid_card),
             db : Session = Depends(get_db)):

    return cards_crud.get_card_by_id(card_id,db)



@router.get("/{card_id}/cvv", response_model=cards.CardSecretResponse)
def get_debit_card_cvv(card_id: int,
                       valid_debit_card: models.Card = Depends(get_valid_card)):

    return {"cvv": utils.decode_cvv(valid_debit_card.CVV_encrypted)}



@router.get("/", response_model=cards.AllCardsDashboard)
def get_all_cards(user : models.User = Depends(get_current_user),
                  db : Session = Depends(get_db)
                  ):

    return cards.get_all_cards(user.id, db)