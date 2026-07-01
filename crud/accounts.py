from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import models,schemas
import utils


def create_account(account : schemas.AccCreate, user_id : int, db : Session):


    new_account: models.Account = models.Account(owner_id=user_id,
                                                 type= account.type,
                                                 iban=utils.generate_iban(),
                                                 balance= account.balance)

    db.add(new_account)

    try:
        db.commit()

        db.refresh(new_account)
        return new_account

    except IntegrityError:
        db.rollback()
        return False


def get_all_accounts(user_id : int, db : Session):

    #find all the accounts for the user id from the token
    user_accounts = db.query(models.Account).filter(models.Account.owner_id == user_id).all()

    return  user_accounts


#thin function will be used only to find the recipient for transfer
#we will check if recipient name matches the owner name in router/transfers
def get_acc_by_id(acc_id:int, db:Session):
    return db.query(models.Account).filter(models.Account.id == acc_id).first()

def get_acc_by_iban(iban, db:Session):
    return db.query(models.Account).filter(models.Account.iban == iban).first()
