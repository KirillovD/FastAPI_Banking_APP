from sqlalchemy.orm import Session

import models
import utils
from enums import AccountType
from schemas import accounts


def _generate_unique_iban(db: Session, max_attempts: int = 5) -> str | None:
    for _ in range(max_attempts):
        iban = utils.generate_iban()
        if get_acc_by_iban(iban, db) is None:
            return iban

    return None


def add_account(
    account: accounts.AccCreate | accounts.CreditAccCreate,
    user_id: int,
    db: Session,
):
    iban = _generate_unique_iban(db)
    if iban is None:
        return False

    new_account = models.Account(
        owner_id=user_id,
        type=account.type,
        iban=iban,
        balance=account.balance,
    )

    db.add(new_account)
    return new_account


def create_account(
    account: accounts.AccCreate | accounts.CreditAccCreate,
    user_id: int,
    db: Session,
):
    new_account = add_account(account, user_id, db)
    if not new_account:
        return False

    db.commit()
    db.refresh(new_account)
    return new_account


def get_all_user_accounts(user_id: int, db: Session):
    return (
        db.query(models.Account)
        .filter(models.Account.owner_id == user_id)
        .all()
    )


def get_acc_by_id(acc_id: int, db: Session):
    return db.query(models.Account).filter(models.Account.id == acc_id).first()


def get_acc_by_iban(iban: str, db: Session):
    return db.query(models.Account).filter(models.Account.iban == iban).first()


def get_all_accounts(acc_type: AccountType, db: Session):
    return db.query(models.Account).filter(models.Account.type == acc_type)
