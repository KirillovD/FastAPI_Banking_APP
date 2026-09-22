from datetime import date

from sqlalchemy.orm import Session

import models


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


def get_unsettled_statements(
    account_id: int,
    db: Session,
):
    return (
        db.query(models.CreditStatement)
        .filter(
            models.CreditStatement.account_id == account_id,
            models.CreditStatement.amount_paid
            < models.CreditStatement.statement_balance,
        )
        .order_by(
            models.CreditStatement.due_date.asc(),
            models.CreditStatement.period_end.asc(),
            models.CreditStatement.id.asc(),
        )
        .all()
    )


def get_due_unevaluated_statements(
    as_of_date: date,
    db: Session,
):
    return (
        db.query(models.CreditStatement)
        .filter(
            models.CreditStatement.due_date < as_of_date,
            models.CreditStatement.evaluated_at.is_(None),
        )
        .order_by(
            models.CreditStatement.due_date.asc(),
            models.CreditStatement.id.asc(),
        )
        .all()
    )


def get_due_unevaluated_statements_for_account(
    account_id: int,
    as_of_date: date,
    db: Session,
):
    return (
        db.query(models.CreditStatement)
        .filter(
            models.CreditStatement.account_id == account_id,
            models.CreditStatement.due_date < as_of_date,
            models.CreditStatement.evaluated_at.is_(None),
        )
        .order_by(
            models.CreditStatement.due_date.asc(),
            models.CreditStatement.id.asc(),
        )
        .all()
    )


def get_deficient_statements(
    account_id: int,
    as_of_date: date,
    db: Session,
):
    return (
        db.query(models.CreditStatement)
        .filter(
            models.CreditStatement.account_id == account_id,
            models.CreditStatement.due_date < as_of_date,
            models.CreditStatement.amount_paid
            < models.CreditStatement.minimum_payment,
        )
        .order_by(
            models.CreditStatement.due_date.asc(),
            models.CreditStatement.id.asc(),
        )
        .all()
    )


def has_active_deficiency(
    account_id: int,
    as_of_date: date,
    db: Session,
) -> bool:
    return (
        db.query(models.CreditStatement.id)
        .filter(
            models.CreditStatement.account_id == account_id,
            models.CreditStatement.due_date < as_of_date,
            models.CreditStatement.amount_paid
            < models.CreditStatement.minimum_payment,
        )
        .first()
        is not None
    )
