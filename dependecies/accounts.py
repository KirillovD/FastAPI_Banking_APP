from fastapi import Depends
from sqlalchemy.orm import Session

import exceptions
import models
from crud import accounts
from database import get_db
from schemas.common import ResourceId
from dependecies.users import get_current_user
from enums import AccountType


def get_valid_acc(
    acc_id: ResourceId,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = accounts.get_acc_by_id(acc_id, db)

    if not account:
        raise exceptions.AccountNotFound()

    if account.owner_id != user.id:
        raise exceptions.NotYourAccount()

    return account


def get_valid_credit_acc(
    acc_id: ResourceId,
    account: models.Account = Depends(get_valid_acc),
):
    if account.type != AccountType.CREDIT:
        raise exceptions.AccountOperationNotAllowed(
            detail="This endpoint requires a credit account"
        )

    return account
