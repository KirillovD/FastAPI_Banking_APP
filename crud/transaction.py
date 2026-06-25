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

    money_limit = float(sum(attrgetter("acc_balance","overdraft_limit")(source_account)))

    return money_limit >= transfer_amount


def transfer_money(source_account, recipient_account, transfer_amount,db : Session):

    source_account.acc_balance -= transfer_amount
    recipient_account.acc_balance += transfer_amount

    transfer = create_transaction_record( source_account.acc_id,
                                recipient_account.acc_id,
                                transfer_amount,
                                "transfer",
                                "transfer",
                                db
                                     )

    db.commit()
    db.refresh(transfer)

    return transfer


def get_transactions_history(user_id,db : Session):
    user_accounts = accounts.get_all_accounts(user_id,db)
    account_ids = [account.acc_id for account in user_accounts]

    user_transactions_history = (db.query(models.Transaction).
                                 filter(
        or_(
        models.Transaction.sender_account_id.in_(account_ids),
        models.Transaction.recipient_account_id.in_(account_ids)
                                            )
                                 ).all()
                                 )

    return user_transactions_history



def create_transaction_record(sender_account_id : int | None,
                                             recipient_account_id : int | None,
                                             amount : float,
                                             operation_type : str,
                                             category : str,
                                             db : Session,
                                             description: str | None = None,
                                             status : str = "successful"):

    new_transaction_record = models.Transaction(sender_account_id = sender_account_id,
                                             recipient_account_id = recipient_account_id,
                                             transfer_amount = amount,
                                             status = status,
                                             operation_type = operation_type,
                                             category= category,
                                             description = description
                                             )

    db.add(new_transaction_record)

    return new_transaction_record


def cash_deposit_money(acc_id : int, deposit_amount : float, db : Session):

    account = db.query(models.Account).filter(models.Account.acc_id == acc_id).first()

    account.acc_balance += deposit_amount


    create_transaction_record( None,
                                acc_id,
                                deposit_amount,
                                "deposit",
                                "cash_deposit",
                                db
                                             )

    db.commit()
    db.refresh(account)

    return account


def cash_withdraw_money(acc_id: int, withdraw_amount : float, db: Session):
    account = db.query(models.Account).filter(models.Account.acc_id == acc_id).first()

    account.acc_balance -= withdraw_amount



    create_transaction_record( acc_id,
                                None,
                                withdraw_amount,
                                "withdrawal",
                                "cash_withdrawal",
                                db
                                     )

    db.commit()
    db.refresh(account)

    return account