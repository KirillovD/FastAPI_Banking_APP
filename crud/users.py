from sqlalchemy.orm import Session
import models
from schemas import users


def get_user_by_email(email: str, db: Session):
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(user: users.UserCreate, hashed_pwd, db : Session):

    db_user = models.User(first_name=user.first_name, last_name=user.last_name,
                          email=user.email, password=hashed_pwd)

    db.add(db_user)
    return db_user


def find_user(user_id,db : Session):
    return db.query(models.User).filter(models.User.id == user_id).first()

