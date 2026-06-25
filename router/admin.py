from sqlalchemy.orm import Session
import dependencies
from database import get_db
from fastapi import Depends,APIRouter
from crud import admin

router = APIRouter(
    prefix="/admin",
    tags=["Admin Operations"],
    dependencies = [Depends(dependencies.verify_existing_token), Depends(dependencies.check_admin)]
)


@router.get("/")
def get_all_accounts_admin(db : Session = Depends(get_db)):

    return admin.get_all_accounts_admin(db)



