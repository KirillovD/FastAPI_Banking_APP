from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

import exceptions
import models
from crud import cards, transaction
from enums import (
    AccountType,
    OperationType,
    PaymentType,
    TransactionClassificationSource,
    TransactionStatus,
)
from schemas import transactions
from services import credit_score
from services.categorizer import categorizer
from utils import decode_cvv, verify_password


def check_cvv(send_cvv: str | None, db_cvv_encrypted):
    if not send_cvv:
        raise exceptions.CvvMissing()

    db_cvv = decode_cvv(db_cvv_encrypted)
    if send_cvv != db_cvv:
        raise exceptions.CvvCodeIncorrect()

    return True


def check_pin_code(send_pin: str | None, db_pin_hashed):
    if not send_pin:
        raise exceptions.PinMissing()

    if not verify_password(send_pin, db_pin_hashed):
        raise exceptions.PinCodeIncorrect()

    return True


def is_account_balance_sufficient(source_account, transfer_amount):
    available_funds = (
        Decimal(str(source_account.balance))
        + Decimal(str(source_account.limit))
    )

    return available_funds >= Decimal(str(transfer_amount))


def _is_card_expired(card: models.Card) -> bool:
    expiry = card.expiry_date
    now = datetime.now(timezone.utc)

    if expiry.tzinfo is None:
        now = now.replace(tzinfo=None)

    return expiry <= now


def _credit_utilization(
    account: models.Account,
    *,
    balance: Decimal | None = None,
) -> Decimal:
    if (
        account.type != AccountType.CREDIT
        or account.limit <= Decimal("0")
    ):
        return Decimal("0")

    effective_balance = (
        Decimal(account.balance)
        if balance is None
        else Decimal(balance)
    )
    debt = max(
        -effective_balance,
        Decimal("0"),
    )

    return debt / Decimal(account.limit)


def _record_rapid_limit_depletion(
    account: models.Account,
    payment_amount: Decimal,
):
    if account.type != AccountType.CREDIT:
        return

    before = _credit_utilization(account)
    after = _credit_utilization(
        account,
        balance=(
            Decimal(account.balance)
            - Decimal(payment_amount)
        ),
    )

    if (
        before < Decimal("0.50")
        and after >= Decimal("0.80")
    ):
        if account.credit_account_metrics is None:
            account.credit_account_metrics = (
                models.CreditAccountMetrics()
            )

        account.credit_account_metrics.rapid_limit_depletion_count += 1


def check_card_for_payment(
    payment_info: transactions.CardPaymentCreate,
    user: models.User,
    db: Session,
):
    card = cards.get_card_by_number(
        card_number=payment_info.terminal_data.card_number,
        db=db,
    )

    if not card:
        raise exceptions.CardNotFound()

    if card.user_id != user.id:
        raise exceptions.NotYourCard()

    if _is_card_expired(card):
        raise exceptions.CardExpired()

    return card


def process_payment(
    payment_info: transactions.CardPaymentCreate,
    user: models.User,
    db: Session,
):
    card = check_card_for_payment(payment_info, user, db)

    if payment_info.terminal_data.payment_type == PaymentType.ONLINE:
        check_cvv(payment_info.cvv, card.CVV_encrypted)

    elif payment_info.terminal_data.payment_type == PaymentType.POS:
        check_pin_code(payment_info.pin_block, card.pin_code_hashed)

    account = card.linked_account

    if not is_account_balance_sufficient(account, payment_info.amount):
        raise exceptions.InsufficientFunds()

    categorizer_response = categorizer.categorize(
        payment_info.terminal_data.merchant_name,
        mcc_code=payment_info.terminal_data.mcc_code,
        rule_source=TransactionClassificationSource.MERCHANT_RULE,
    )

    _record_rapid_limit_depletion(
        account,
        payment_info.amount,
    )
    transaction.withdraw_funds(account, payment_info.amount)

    transaction_data = transactions.TransactionCreateRecord(
        amount=payment_info.amount,
        status=TransactionStatus.SUCCESSFUL,
        created_at=datetime.now(timezone.utc),
        operation_type=OperationType.PAYMENT,
        sender_account_id=account.id,
        sender_iban=account.iban,
        description=payment_info.terminal_data.merchant_name,
        category=categorizer_response["category"],
        mcc_code=categorizer_response["mcc_code"],
        classification_source=(
            categorizer_response["classification_source"]
        ),
    )

    new_transaction = transaction.create_transaction_record(
        transaction_data,
        db,
    )

    # Session autoflush is disabled in this project, so flush the
    # transaction and metric state before deterministic score queries.
    db.flush()
    credit_score.recalculate_user_credit_score(
        user.id,
        db,
        commit=False,
    )

    db.commit()
    db.refresh(new_transaction)

    return transactions.CardPaymentResponse(
        transaction_id=new_transaction.id,
        status=new_transaction.status,
        amount=new_transaction.amount,
        message="Payment approved",
    )
