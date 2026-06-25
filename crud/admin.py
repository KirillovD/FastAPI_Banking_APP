from sqlalchemy.orm import Session

import models


def get_all_accounts_admin(db:Session):
    return db.query(models.Account).all()