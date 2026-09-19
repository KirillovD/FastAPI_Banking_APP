from datetime import date

from sqlalchemy.orm import Session

import models
from enums import CreditStatementStatus


def get_statements(account_id: int, db: Session):
    return (
        db.query(models.CreditStatement)
        .filter(models.CreditStatement.account_id == account_id)
        .order_by(
            models.CreditStatement.period_end.desc(),
            models.CreditStatement.id.desc(),
        )
        .all()
    )


def get_latest_statement(account_id: int, db: Session):
    return (
        db.query(models.CreditStatement)
        .filter(models.CreditStatement.account_id == account_id)
        .order_by(
            models.CreditStatement.period_end.desc(),
            models.CreditStatement.id.desc(),
        )
        .first()
    )


def get_statement_for_period(
    account_id: int,
    period_end: date,
    db: Session,
):
    return (
        db.query(models.CreditStatement)
        .filter(
            models.CreditStatement.account_id == account_id,
            models.CreditStatement.period_end == period_end,
        )
        .first()
    )


def get_repayment_statement(account_id: int, db: Session):
    past_due = (
        db.query(models.CreditStatement)
        .filter(
            models.CreditStatement.account_id == account_id,
            models.CreditStatement.status == CreditStatementStatus.PAST_DUE,
            models.CreditStatement.amount_paid
            < models.CreditStatement.minimum_payment,
        )
        .order_by(
            models.CreditStatement.due_date.asc(),
            models.CreditStatement.id.asc(),
        )
        .first()
    )
    if past_due:
        return past_due

    latest = get_latest_statement(account_id, db)
    if latest and latest.amount_paid < latest.statement_balance:
        return latest

    return None


def get_due_unevaluated_statements(as_of_date: date, db: Session):
    return (
        db.query(models.CreditStatement)
        .filter(
            models.CreditStatement.due_date <= as_of_date,
            models.CreditStatement.evaluated_at.is_(None),
        )
        .order_by(
            models.CreditStatement.due_date.asc(),
            models.CreditStatement.id.asc(),
        )
        .all()
    )


def get_current_past_due_statement(account_id: int, db: Session):
    return (
        db.query(models.CreditStatement)
        .filter(
            models.CreditStatement.account_id == account_id,
            models.CreditStatement.status == CreditStatementStatus.PAST_DUE,
            models.CreditStatement.amount_paid
            < models.CreditStatement.minimum_payment,
        )
        .order_by(
            models.CreditStatement.due_date.asc(),
            models.CreditStatement.id.asc(),
        )
        .first()
    )
