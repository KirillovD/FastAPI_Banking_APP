#file for
from operator import attrgetter

from sqlalchemy.orm import Session

#function to get all user accounts displayed
#again get user id from the token and open the Session
#use list[] in the response model for multiple accounts
def is_balance_sufficient(source_account, transfer_amount):

    money_limit = float(sum(attrgetter("acc_balance","overdraft_limit")(source_account)))

    return money_limit >= transfer_amount


def transfer_money(source_account, recipient_account, transfer_amount,db : Session):
    source_account.acc_balance -= transfer_amount
    recipient_account.acc_balance += transfer_amount
    db.commit()




