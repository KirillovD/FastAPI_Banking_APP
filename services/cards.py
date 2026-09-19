from decimal import Decimal

from sqlalchemy.orm import Session

import exceptions
import models
from crud import accounts as crud_accounts
from crud import cards as crud_cards
from enums import AccountType
from schemas import cards as card_schemas
from schemas.accounts import CreditAccCreate


DEFAULT_CREDIT_LIMIT = Decimal("500.00")
DEBIT_ACCOUNT_TYPES = {
    AccountType.CHECKING,
    AccountType.SAVINGS,
}


def create_credit_card(
    card_type_and_pin: card_schemas.CreateCard,
    user: models.User,
    db: Session,
):
    try:
        account = crud_accounts.add_account(
            CreditAccCreate(),
            user.id,
            db,
        )
        if not account:
            raise exceptions.IbanGenError()

        account.limit = DEFAULT_CREDIT_LIMIT
        account.credit_account_metrics = (
            models.CreditAccountMetrics()
        )

        db.flush()

        credit_card = crud_cards.create_card(
            account.id,
            user.id,
            card_type_and_pin,
            db,
        )

        db.commit()
        db.refresh(credit_card)

        return credit_card

    except Exception:
        db.rollback()
        raise


def create_debit_card(
    card_type_and_pin: card_schemas.CreateCard,
    account: models.Account,
    db: Session,
):
    if account.type not in DEBIT_ACCOUNT_TYPES:
        raise exceptions.AccountOperationNotAllowed(
            detail=(
                "Debit cards can only be issued for "
                "checking and savings accounts"
            )
        )

    try:
        debit_card = crud_cards.create_card(
            account.id,
            account.owner_id,
            card_type_and_pin,
            db,
        )

        db.commit()
        db.refresh(debit_card)

        return debit_card

    except Exception:
        db.rollback()
        raise
