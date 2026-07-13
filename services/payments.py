from operator import attrgetter
from sqlalchemy.orm import Session
import exceptions
from crud import cards, transaction, accounts
from enums import TransactionStatus, OperationType
from services.categorizer import categorizer
from schemas import transactions
from utils import decode_cvv, verify_password


def check_cvv(send_cvv : str | None, db_cvv_encrypted):
    if not send_cvv:
        raise exceptions.CvvMissing()

    db_cvv = decode_cvv(db_cvv_encrypted)
    if not send_cvv == db_cvv:
        raise exceptions.CvvCodeIncorrect

    else:
        return True


def check_pin_code(send_pin : str | None, db_pin_hashed):

    if not send_pin:
        raise exceptions.PinMissing()
    if not verify_password(send_pin, db_pin_hashed):
        raise exceptions.PinCodeIncorrect()

    else:
        return True


def is_account_balance_sufficient(source_account, transfer_amount):

    money_limit = float(sum(attrgetter("balance","limit")(source_account)))

    return money_limit >= transfer_amount


def check_card_for_payment(payment_info: transactions.CardPaymentCreate,
                           db: Session):

    card = cards.get_card_by_number(card_number=payment_info.card_number, db=db)
    if card:
        return card
    else:
        raise exceptions.CardNotFound


def process_payment(payment_info: transactions.CardPaymentCreate,
                    db: Session):

    card = check_card_for_payment(payment_info,db)
    card_cvv = cards.get_cvv(card.id, db)


    if payment_info.terminal_data.payment_type == "online":
        check_cvv(payment_info.cvv, card_cvv)

    elif payment_info.terminal_data.payment_type == "pos":

        check_pin_code(payment_info.pin_block, card.pin_code_hashed)

    if not is_account_balance_sufficient(card.linked_account, payment_info.amount):
        raise exceptions.InsufficientFunds()

    categorizer_response = categorizer.categorize(payment_info.description)


    account = accounts.get_acc_by_id(card.linked_acc_id,db)
    transaction.withdraw_funds(account,payment_info.amount)

    transaction_data = transactions.TransactionCreateRecord(

                                amount=payment_info.amount,
                                status=TransactionStatus.SUCCESSFUL,
                                created_at=payment_info.created_at,
                                operation_type=OperationType.PAYMENT,
                                category=categorizer_response["category"],
                                sender_account_id=account.id,
                                sender_iban=account.iban,
                                description=payment_info.description,
                                transaction_metadata=payment_info.terminal_data.model_dump()
    )

    new_transaction = transaction.create_transaction_record(transaction_data, db)

    db.commit()
    db.refresh(new_transaction)

    return new_transaction








