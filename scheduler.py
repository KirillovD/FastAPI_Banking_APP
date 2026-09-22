from datetime import datetime
import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler

from config import settings
from database import SessionLocal
from services import credit


logging.basicConfig(
    filename="credit_operations.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

BUSINESS_TIMEZONE = ZoneInfo(
    settings.bank_business_timezone
)

scheduler = BlockingScheduler(
    timezone=BUSINESS_TIMEZONE
)


def _business_today():
    return datetime.now(
        BUSINESS_TIMEZONE
    ).date()


@scheduler.scheduled_job(
    "cron",
    hour=0,
    minute=5,
    coalesce=True,
    misfire_grace_time=86400,
    max_instances=1,
)
def evaluate_credit_statement_due_dates():
    with SessionLocal() as db:
        credit.evaluate_due_statements(
            db,
            as_of_date=_business_today(),
        )


@scheduler.scheduled_job(
    "cron",
    day="last",
    hour=23,
    minute=55,
    coalesce=True,
    misfire_grace_time=86400,
    max_instances=1,
)
def create_credit_statements():
    with SessionLocal() as db:
        credit.create_monthly_statements(
            db,
            as_of_date=_business_today(),
        )


@scheduler.scheduled_job(
    "cron",
    hour=23,
    minute=50,
    coalesce=True,
    misfire_grace_time=86400,
    max_instances=1,
)
def calculate_daily_credit_interest():
    with SessionLocal() as db:
        credit.calculate_acquired_interest_all_credit_accounts(
            db,
            as_of_date=_business_today(),
        )


if __name__ == "__main__":
    print(
        "Credit scheduler started "
        f"({settings.bank_business_timezone})"
    )
    scheduler.start()
