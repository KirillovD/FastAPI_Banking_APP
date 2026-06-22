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

    new_transfer_record = models.Transaction(sender_account_id=source_account.acc_id,
                                             recipient_account_id=recipient_account.acc_id,
                                             transfer_amount=transfer_amount,
                                             status= "successful",
                                             operation_type = "transfer"
                                             )
    db.add(new_transfer_record)
    db.commit()
    db.refresh(new_transfer_record)

    return new_transfer_record


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
