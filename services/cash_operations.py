from sqlalchemy.orm import Session

import exceptions
import models
from crud import transaction
from services import payments
from schemas import transactions


def deposit_cash(amount_data : transactions.CashOperation,
                 valid_acc : models.Account,
                 db : Session ):

    account_after_deposit  = transaction.deposit_funds(valid_acc, amount_data.amount)
    db.commit()
    db.refresh(account_after_deposit)

    return account_after_deposit


def withdraw_cash(amount_data : transactions.CashOperation,
                  valid_acc: models.Account,
                  db : Session) :

    if not payments.is_account_balance_sufficient(valid_acc, amount_data.amount):
        raise exceptions.InsufficientFunds()

    account_after_withdraw  = transaction.withdraw_funds(valid_acc, amount_data.amount)

    db.commit()
    db.refresh(account_after_withdraw)

    return account_after_withdraw