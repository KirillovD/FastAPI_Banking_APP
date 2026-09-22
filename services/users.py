from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import exceptions
import utils
from crud import users as user_crud
from schemas import users as user_schemas


def create_user(
    user: user_schemas.UserCreate,
    db: Session,
):
    existing_user = user_crud.get_user_by_email(
        str(user.email),
        db,
    )
    if existing_user:
        raise exceptions.UserAlreadyExists()

    hashed_pwd = utils.hash_password(user.password)

    new_user = user_crud.create_user(
        user,
        hashed_pwd,
        db,
    )

    try:
        db.commit()
        db.refresh(new_user)
        return new_user

    except IntegrityError:
        db.rollback()

        if user_crud.get_user_by_email(
            str(user.email),
            db,
        ):
            raise exceptions.UserAlreadyExists()

        raise
