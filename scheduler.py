import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from database import SessionLocal
from services import credit


logging.basicConfig(
    filename="credit_operations.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

scheduler = BlockingScheduler()


@scheduler.scheduled_job(
    "cron",
    day=15,
    hour=23,
    minute=59,
)
def evaluate_credit_statement_due_dates():
    with SessionLocal() as db:
        credit.evaluate_due_statements(db)


@scheduler.scheduled_job(
    "cron",
    day="last",
    hour=23,
    minute=55,
)
def create_credit_statements():
    with SessionLocal() as db:
        credit.create_monthly_statements(db)


@scheduler.scheduled_job(
    "cron",
    hour=23,
    minute=50,
)
def calculate_daily_credit_interest():
    with SessionLocal() as db:
        credit.calculate_acquired_interest_all_credit_accounts(
            db
        )


if __name__ == "__main__":
    print("Credit scheduler started")
    scheduler.start()
