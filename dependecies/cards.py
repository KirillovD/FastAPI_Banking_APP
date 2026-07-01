from fastapi import Depends
from sqlalchemy.orm import Session

import exceptions
import models
from crud import accounts, cards
from database import get_db
from dependecies.users import get_current_user


def get_valid_debit_card(card_id : int,
                   user : models.User = Depends(get_current_user),
                   db : Session = Depends(get_db)):

    debit_card = cards.get_card_info("DebitCard",card_id,db)

    if not debit_card:
        raise exceptions.CardNotFoundException()

    linked_acc = accounts.get_acc_by_id(debit_card.linked_acc_id,db)

    if not linked_acc or not linked_acc.owner_id == user.id:
        raise exceptions.NotYourCardException()

    return debit_card

def get_valid_credit_card(card_id : int,
                          user : models.User = Depends(get_current_user),
                          db : Session = Depends(get_db)):

    credit_card = cards.get_card_info("CreditCard", card_id, db)
    if not credit_card:
        raise exceptions.CardNotFoundException()

    if not credit_card.owner_id == user.id:
        raise exceptions.NotYourCardException()

    return credit_card