from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
import utils
from enums import AccountType
from mock_data_generator.seed_demo import (
    DEMO_EMAIL,
    seed_demo_data,
)
from services import analytics


def test_demo_seed_is_idempotent_and_populates_portfolio_views():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.Base.metadata.create_all(bind=engine)
    factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    fixed_now = datetime(
        2026,
        9,
        22,
        12,
        tzinfo=timezone.utc,
    )

    try:
        with factory() as db:
            created = seed_demo_data(
                db,
                password="portfolio-demo-password",
                now=fixed_now,
            )
            assert created is True

            user = (
                db.query(models.User)
                .filter(models.User.email == DEMO_EMAIL)
                .one()
            )
            assert utils.verify_password(
                "portfolio-demo-password",
                user.password,
            )

            accounts = (
                db.query(models.Account)
                .filter(models.Account.owner_id == user.id)
                .all()
            )
            assert {
                account.type for account in accounts
            } == {
                AccountType.CHECKING,
                AccountType.SAVINGS,
                AccountType.CREDIT,
            }

            assert (
                db.query(models.Card)
                .filter(models.Card.user_id == user.id)
                .count()
                == 1
            )
            assert (
                db.query(models.CreditStatement)
                .join(models.Account)
                .filter(models.Account.owner_id == user.id)
                .count()
                == 2
            )
            assert (
                db.query(models.Transaction).count()
                == 26
            )
            assert 300 <= user.credit_score <= 850
            assert user.credit_score != 500

            summary = analytics.get_spending_summary(
                user.id,
                90,
                db,
                now=fixed_now,
            )
            insights = analytics.get_customer_insights(
                user.id,
                90,
                db,
                now=fixed_now,
            )

            assert summary.total_spend > 0
            assert summary.transaction_count > 10
            assert summary.categories
            assert insights.profile_tags
            assert insights.suggested_offers

            created_again = seed_demo_data(
                db,
                password="portfolio-demo-password",
                now=fixed_now,
            )
            assert created_again is False

            assert (
                db.query(models.User)
                .filter(models.User.email == DEMO_EMAIL)
                .count()
                == 1
            )
            assert db.query(models.Transaction).count() == 26

    finally:
        engine.dispose()
