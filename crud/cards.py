from typing import Literal

from sqlalchemy.orm import Session
from models import Card
import utils
from schemas import cards



def create_card(acc_id : int, user_id: int, card_type_and_pin : cards.CreateCard, db : Session):

    debit_card_info = utils.generate_card_info(card_type_and_pin.type, card_type_and_pin.pin_code)

    new_card = Card(linked_acc_id = acc_id,
                    user_id= user_id,
                    number=debit_card_info["card_number"],
                    expiry_date=debit_card_info["expiry_date"],
                    pin_code_hashed=debit_card_info["hashed_pin_code"],
                    CVV_encrypted=debit_card_info["encrypted_security_code"]
                    )

    db.add(new_card)

    return new_card


def get_card_by_id(card_id : int, db : Session):

    return db.query(Card).get(card_id)


def get_cvv(card_id : int, db : Session) -> str:

    card = db.query(Card).get(card_id)

    return utils.decode_cvv(card.CVV_encrypted)


def get_all_cards(user_id : int, db : Session):

    user_cards = db.query(Card).filter(Card.user_id == user_id).all()
    return user_cards


def get_card_by_number(card_number : str, db : Session):

    return db.query(Card).filter(Card.number==card_number).first()



