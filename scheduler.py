from apscheduler.schedulers.blocking import BlockingScheduler
from database import SessionLocal
from services import cards

scheduler = BlockingScheduler()

@scheduler.scheduled_job("cron", day = 15, hour= 12, minute= 0)
def credit_card_payment_deadline_check():
    with SessionLocal() as db:
        cards.all_credit_cards_deadline_check(db)


@scheduler.scheduled_job("cron", day = "last", hour= 12, minute= 0)
def create_credit_card_statement():
    with SessionLocal() as db:
        cards.add_acquired_interest_all_credit_accounts(db)


@scheduler.scheduled_job("cron", hour= 23, minute= 59)
def calculate_daily_acquired_interest():
    with SessionLocal() as db:
        cards.calculate_acquired_interest_all_credit_accounts(db)

if __name__ == "__main__":
    print("Планировщик запущен и ожидает задачи...")
    scheduler.start()
