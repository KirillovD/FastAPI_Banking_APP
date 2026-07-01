from fastapi import Depends
from sqlalchemy.orm import Session

import exceptions
from crud import users
from database import get_db
from dependecies.auth import verify_existing_token


def get_current_user(user_id : int = Depends(verify_existing_token),
                     db : Session = Depends(get_db)):

    current_user = users.find_user(user_id,db)
    if not current_user:
        raise exceptions.UserNotFoundException()

    return current_user