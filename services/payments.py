from operator import attrgetter
from sqlalchemy.orm import Session
import exceptions
import schemas
from crud import cards
from crud.accounts import get_acc_by_id
from utils import decode_cvv, hash_password, verify_password


def check_cvv(send_cvv : str, db_cvv_encrypted):
    if not send_cvv:
        raise exceptions.CvvMissing()

    db_cvv = decode_cvv(db_cvv_encrypted)
    if not send_cvv == db_cvv:
        raise exceptions.CvvCodeIncorrect

    else:
        return True


def check_pin_code(send_pin : str, db_pin_hashed):

    if not send_pin:
        raise exceptions.PinMissing()
    if not verify_password(send_pin, db_pin_hashed):
        raise exceptions.PinCodeIncorrect()

    else:
        return True


def is_account_balance_sufficient(source_account, transfer_amount):

    money_limit = float(sum(attrgetter("balance","overdraft_limit")(source_account)))

    return money_limit >= transfer_amount


def is_credit_balance_sufficient(credit_card, transfer_amount):
    money_limit = float(credit_card.credit_limit - credit_card.balance)

    return money_limit >= transfer_amount


def check_card_for_payment(payment_info: schemas.CardPaymentCreate,
                           db: Session):

    card = cards.get_card_by_number(card_type=payment_info.card_type,
                                    card_number=payment_info.card_number,
                                    db=db)
    if card:
        return card
    else:
        raise exceptions.CardNotFound


def process_payment(payment_info: schemas.CardPaymentCreate,
                    db: Session):

    card = check_card_for_payment(payment_info,db)
    card_cvv = cards.get_cvv(payment_info.card_type, card.id, db)


    if payment_info.payment_type == "online":
        check_cvv(payment_info.cvv, card_cvv)

    elif payment_info.payment_type == "pos":

        check_pin_code(payment_info.pin_block, card.pin_code_hashed)

    if payment_info.card_type == "credit":
        if not is_credit_balance_sufficient(card, payment_info.amount):
            raise exceptions.InsufficientFunds()

    elif payment_info.card_type == "debit":
        if not is_account_balance_sufficient(card.linked_account, payment_info.amount):
            raise exceptions.InsufficientFunds()



    return cards.process_payment(card,payment_info.amount,db)













