from fastapi import Depends
from sqlalchemy.orm import Session

import exceptions
import models
from crud import accounts, cards
from database import get_db
from dependecies.users import get_current_user


def get_valid_card(card_id : int,
                   user : models.User = Depends(get_current_user),
                   db : Session = Depends(get_db)):

    card = cards.get_card_by_id(card_id, db)

    if not card:
        raise exceptions.CardNotFound()

    linked_acc = accounts.get_acc_by_id(card.linked_acc_id,db)

    if not linked_acc or not linked_acc.owner_id == user.id:
        raise exceptions.NotYourCard()

    return card

