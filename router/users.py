from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

import models
from database import get_db
from dependecies.users import get_current_user
from services import users as user_services
from schemas import users

router = APIRouter(
    prefix="/users",
    tags=["Users Operations"],
)


@router.post(
    "/",
    response_model=users.UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    user: users.UserCreate,
    db: Session = Depends(get_db),
):
    return user_services.create_user(user, db)


@router.get("/", response_model=users.UserResponse)
def find_user(user: models.User = Depends(get_current_user)):
    return user
