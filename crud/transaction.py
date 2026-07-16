#file for
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import or_
from schemas import transactions
import models
from crud import accounts


#function to get all user accounts displayed
#again get user id from the token and open the Session
#use list[] in the response model for multiple accounts


def withdraw_funds(account: models.Account, amount: Decimal):
    account.balance -= amount
    return account

def deposit_funds(account: models.Account, amount: Decimal):
    account.balance += amount
    return account


def get_transactions_history(user_id,db : Session):
    user_accounts = accounts.get_all_user_accounts(user_id, db)
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



def create_transaction_record(transaction_data : transactions.TransactionCreateRecord,
                                db : Session):

    new_transaction_record = models.Transaction(**transaction_data.model_dump())

    db.add(new_transaction_record)

    return new_transaction_record

