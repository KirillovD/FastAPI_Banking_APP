from sqlalchemy.orm import Session
import models,schemas


def create_account(account : schemas.AccCreate, user_id : int, db : Session):
    new_account: models.Account = models.Account(owner_id=user_id, acc_type= account.acc_type,
                                 acc_balance= account.acc_balance)

    db.add(new_account)
    db.commit()
    db.refresh(new_account)

    return new_account


def get_all_accounts(user_id : int, db : Session):

    #find all the accounts for the user id from the token
    user_accounts = db.query(models.Account).filter(models.Account.owner == user_id).all()

    return  user_accounts


def find_source_acc(user_id_token,acc_id, db:Session):

      return db.query(models.Account).filter(models.Account.owner_id==user_id_token,
                                                        models.Account.acc_id == acc_id).first()


def find_recipient_acc(recipient_acc_id:int, db:Session):
    return db.query(models.Account).filter(models.Account.acc_id == recipient_acc_id).first()