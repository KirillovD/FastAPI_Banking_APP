from decimal import Decimal

from sqlalchemy.orm import Session
from datetime import datetime

import exceptions
import models
from crud import accounts as crud_accounts
from crud import cards as crud_cards
from crud import transaction as crud_transaction

from enums import AccountType
from schemas import cards as card_schemas
from schemas.accounts import AccCreate
from schemas.cards import PayDownBalanceInput
from config import settings
from datetime import date


import logging

# Эту настройку делают один раз (например, при старте приложения)
logging.basicConfig(
    filename='credit_operations.log', # Файл, куда всё будет падать
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def create_credit_card(card_type_and_pin : card_schemas.CreateCard,
                       user : models.User,
                       db : Session):

    new_credit_acc_data = AccCreate(type=AccountType.CREDIT)

    account = crud_accounts.create_account(new_credit_acc_data,user.id,db)
    credit_card = crud_cards.create_card(account.id, user.id, card_type_and_pin, db)

    db.commit()
    db.refresh(credit_card)

    return credit_card


def create_debit_card(card_type_and_pin : card_schemas.CreateCard,
                      account : models.Account,
                      db : Session):
    debit_card= crud_cards.create_card(account.id, account.owner_id, card_type_and_pin, db)

    db.commit()
    db.refresh(debit_card)

    return debit_card


def pay_down_the_balance(valid_credit_card : models.Card,
                         amount_and_id : PayDownBalanceInput,
                         db : Session):

    account=valid_credit_card.linked_account
    min_payment = calculate_min_credit_account_payment(account)
    was_grace_active = account.grace_period_active
    if amount_and_id.amount < min_payment:
        raise exceptions.MinPaymentNotReached

    refreshed_account=  crud_transaction.deposit_funds(account, amount_and_id.amount)

    if refreshed_account.balance >= Decimal("0.0"):
        refreshed_account.grace_period_active = True

        if was_grace_active:
            refreshed_account.acquired_interest = Decimal("0.0")


    db.commit()
    db.refresh(refreshed_account)

    return refreshed_account




def calculate_min_credit_account_payment(account : models.Account):

    if account.balance >= Decimal("0.0"):
        return Decimal("0.0")

    min_payment_percent = abs(account.balance *
                           settings.credit_card_min_payment_percent)


    if min_payment_percent > settings.credit_card_min_payment_amount:
        return  min_payment_percent
    else:
        return settings.credit_card_min_payment_amount


def credit_account_deadline_check(account:models.Account):
    #return False is the Balance is not paid off

    return account.balance >= Decimal("0.0")


def all_credit_cards_deadline_check(db : Session):
    credit_accounts = crud_accounts.get_all_accounts(AccountType.CREDIT, db)
    lost_grace_count = 0
    error_counter = 0

    for account in credit_accounts:
        try:
            new_grace_status = credit_account_deadline_check(account)

            if account.grace_period_active and not new_grace_status:
                lost_grace_count += 1
                logging.info(f"Account id {account.id}: The balance isn't paid off. The Grace Period has ended.")

            account.grace_period_active = new_grace_status

            db.commit()

        except Exception as e:
            error_counter = 0
            db.rollback()
            logging.error(f"Error while checking grace period for account {account.id}:{e}")

    logging.info(f"The deadline check is finished. Grace period ended for {lost_grace_count} accounts. Error counter: {error_counter}")




#we run this every midnight and calculate interest daily for the changing balance
def calculate_credit_account_acquired_interest( account: models.Account):

    account.acquired_interest += abs(account.balance * settings.credit_card_default_dpr)

    return account



def calculate_acquired_interest_all_credit_accounts(db : Session):

    credit_accounts= crud_accounts.get_all_accounts(AccountType.CREDIT, db)
    account_success_counter = 0
    account_fail_counter = 0

    for account in credit_accounts:
        try:

            calculate_credit_account_acquired_interest(account)
            account_success_counter += 1

            db.commit()
            logging.info(f"Interest calculated for account id: {account.id}. Total interest acquired: {account.acquired_interest} ")

        except Exception as e:
            account_fail_counter += 1
            db.rollback()
            logging.error(f"Failed to  calculate interest  account id: {account.id}. Error: {e}")

    logging.info(f"Daily interest calculated successfully for: {account_success_counter} accounts. Error count: {account_fail_counter}")



#if after the grace period the balance is not paid off we add the accumulated interest to it
def add_acquired_interest_to_balance(account : models.Account):

        if account.grace_period_active:
            raise exceptions.GraceNoInterest

        if account.balance < Decimal("0.0"):
            crud_transaction.withdraw_funds(account, account.acquired_interest)
            account.acquired_interest = Decimal("0.0")
            return account


def add_acquired_interest_all_credit_accounts( db : Session):

    credit_accounts= crud_accounts.get_all_accounts(AccountType.CREDIT, db)

    acc_success_counter = 0
    acc_fail_counter = 0

    for account in credit_accounts:
        try:
         add_acquired_interest_to_balance(account)
         acc_success_counter += 1
         db.commit()

         logging.info(
             f"Acquired interest added to balance account id: {account.id}")

        except exceptions.GraceNoInterest as e:
            logging.info(f"Grace period is still active account id: {account.id}. Exception: {e}")


        except Exception as e:
            acc_fail_counter += 1
            db.rollback()
            logging.error(f"Failed to  calculate interest  account id: {account.id}. Error: {e}")

    logging.info(f"Monthly addition of acquired interest successful for: {acc_success_counter} accounts. Error count: {acc_fail_counter}")
