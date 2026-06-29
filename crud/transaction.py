#file for
from operator import attrgetter

from sqlalchemy.orm import Session
from sqlalchemy import or_

import models
from crud import accounts


#function to get all user accounts displayed
#again get user id from the token and open the Session
#use list[] in the response model for multiple accounts
def is_balance_sufficient(source_account, transfer_amount):

    money_limit = float(sum(attrgetter("balance","overdraft_limit")(source_account)))

    return money_limit >= transfer_amount


def transfer_money(source_account, recipient_account, transfer_amount,db : Session):

    source_account.balance -= transfer_amount
    recipient_account.balance += transfer_amount

    transfer = create_transaction_record(
                                sender_account_id = source_account.id,
                                recipient_account_id = recipient_account.id,
                                sender_iban = source_account.iban,
                                recipient_iban = recipient_account.iban,
                                amount = transfer_amount,
                                operation_type = "transfer",
                                category = "transfer",
                                db = db
                                     )

    db.commit()
    db.refresh(transfer)

    return transfer


def get_transactions_history(user_id,db : Session):
    user_accounts = accounts.get_all_accounts(user_id,db)
    account_ids = [account.id for account in user_accounts]

    user_transactions_history = (db.query(models.Transaction).
                                 filter(
        or_(
        models.Transaction.sender_account_id.in_(account_ids),
        models.Transaction.recipient_account_id.in_(account_ids)
                                            )
                                 ).all()
                                 )

    return user_transactions_history



def create_transaction_record(
                                sender_account_id : int | None,
                                recipient_account_id : int | None,
                                sender_iban,
                                recipient_iban,
                                amount : float,
                                operation_type : str,
                                category : str,
                                db : Session,
                                description: str | None = None,
                                status : str = "successful"):

    new_transaction_record = models.Transaction(sender_account_id = sender_account_id,
                                             recipient_account_id = recipient_account_id,
                                             sender_iban = sender_iban,
                                             recipient_iban=recipient_iban,
                                             transfer_amount = amount,
                                             status = status,
                                             operation_type = operation_type,
                                             category= category,
                                             description = description
                                             )

    db.add(new_transaction_record)

    return new_transaction_record


def deposit_cash(acc_id : int, deposit_amount : float, db : Session):

    account = db.query(models.Account).filter(models.Account.id == acc_id).first()

    account.balance += deposit_amount


    create_transaction_record( sender_account_id=None,
                               recipient_account_id=acc_id,
                               sender_iban= None,
                               recipient_iban= account.iban,
                               amount = deposit_amount,
                               operation_type="deposit",
                               category="cash_deposit",
                                db=db
                                             )

    db.commit()
    db.refresh(account)

    return account


def withdraw_cash(acc_id: int, withdraw_amount : float, db: Session):
    account = db.query(models.Account).filter(models.Account.id == acc_id).first()

    account.balance -= withdraw_amount



    create_transaction_record( sender_account_id = acc_id,
                               recipient_account_id = None,
                               sender_iban = account.iban,
                               recipient_iban= None,
                               amount = withdraw_amount,
                               operation_type = "withdraw",
                               category = "cash_withdraw",
                                db=db
                                             )

    db.commit()
    db.refresh(account)

    return account