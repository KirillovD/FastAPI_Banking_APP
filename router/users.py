from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models

import schemas

router = APIRouter(
    prefix="/users",
    tags=["Users Operations"]
)

@router.post("/")
def create_user(user: schemas.UserCreate, db : Session = Depends(get_db)):
    db_user = models.User(first_name=user.first_name, last_name=user.last_name,
                          email=user.email, password=user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user