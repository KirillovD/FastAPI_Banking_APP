from sqlalchemy.orm import Session

import models
from crud import accounts, cards
from enums import AccountType
from schemas import cards as card_schemas
from schemas.accounts import AccCreate


def create_credit_card(card_type_and_pin : card_schemas.CreateCard,
                       user : models.User,
                       db : Session):

    new_credit_acc_data = AccCreate(type=AccountType.CREDIT)

    account = accounts.create_account(new_credit_acc_data,user.id,db)
    credit_card = cards.create_card(account.id, user.id, card_type_and_pin, db)

    db.commit()
    db.refresh(credit_card)

    return credit_card


def create_debit_card(card_type_and_pin : card_schemas.CreateCard,
                      account : models.Account,
                      db : Session):
    debit_card= cards.create_card(account.id, account.owner_id, card_type_and_pin, db)

    db.commit()
    db.refresh(debit_card)

    return debit_card