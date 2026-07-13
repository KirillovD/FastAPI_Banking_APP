from sqlalchemy.orm import Session

import exceptions
import utils
from schemas import users
from crud import users


def create_user(user: users.UserCreate,
                db : Session):

    existing_user = users.get_user_by_email(user.email,db)
    if existing_user:
        raise exceptions.UserAlreadyExists()

    #we take the input password from user and hash it
    hashed_pwd = utils.hash_password(user.password)

    new_user = users.create_user(user,hashed_pwd,db)

    db.commit()
    db.refresh(new_user)

    return new_user