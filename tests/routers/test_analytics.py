from datetime import datetime, timedelta, timezone
from decimal import Decimal

import models
from enums import (
    OperationType,
    TransactionCategory,
    TransactionClassificationSource,
    TransactionStatus,
)
from tests.conftest import (
    TestingSessionLocal,
    create_account,
    create_user_and_login,
)


def _user_id(email: str) -> int:
    with TestingSessionLocal() as db:
        return (
            db.query(models.User)
            .filter(models.User.email == email)
            .one()
            .id
        )


def _transaction(
    *,
    sender_account_id: int,
    amount: str,
    category: TransactionCategory,
    description: str,
    created_at: datetime,
    operation_type: OperationType = OperationType.PAYMENT,
    recipient_account_id: int | None = None,
    status: TransactionStatus = TransactionStatus.SUCCESSFUL,
    mcc_code: str | None = "5411",
):
    return models.Transaction(
        sender_account_id=sender_account_id,
        recipient_account_id=recipient_account_id,
        amount=Decimal(amount),
        created_at=created_at,
        status=status,
        operation_type=operation_type,
        description=description,
        category=category,
        mcc_code=mcc_code,
        classification_source=(
            TransactionClassificationSource.MCC
            if mcc_code
            else TransactionClassificationSource.DESCRIPTION_RULE
        ),
    )


def test_spending_summary_is_user_scoped_and_excludes_internal_transfers(
    client,
    auth_headers,
):
    checking = create_account(
        client,
        auth_headers,
        "checking",
        1000,
    )
    savings = create_account(
        client,
        auth_headers,
        "savings",
        500,
    )

    other_headers = create_user_and_login(
        client,
        "mary@example.com",
        "Mary",
    )
    other = create_account(
        client,
        other_headers,
        "checking",
        900,
    )

    now = datetime.now(timezone.utc)

    with TestingSessionLocal() as db:
        db.add_all(
            [
                _transaction(
                    sender_account_id=checking["id"],
                    amount="120.00",
                    category=TransactionCategory.GROCERIES,
                    description="REWE Munich",
                    created_at=now - timedelta(days=1),
                ),
                _transaction(
                    sender_account_id=checking["id"],
                    amount="60.00",
                    category=TransactionCategory.RESTAURANTS,
                    description="L'Osteria",
                    created_at=now - timedelta(days=2),
                    mcc_code="5812",
                ),
                _transaction(
                    sender_account_id=checking["id"],
                    recipient_account_id=savings["id"],
                    amount="300.00",
                    category=TransactionCategory.OTHER,
                    description="Move to savings",
                    created_at=now - timedelta(days=1),
                    operation_type=OperationType.TRANSFER,
                    mcc_code=None,
                ),
                _transaction(
                    sender_account_id=checking["id"],
                    amount="500.00",
                    category=TransactionCategory.E_COMMERCE,
                    description="Old Amazon",
                    created_at=now - timedelta(days=40),
                    mcc_code="5399",
                ),
                _transaction(
                    sender_account_id=other["id"],
                    amount="999.00",
                    category=TransactionCategory.GAMBLING,
                    description="Other user's transaction",
                    created_at=now - timedelta(days=1),
                    mcc_code="7995",
                ),
                _transaction(
                    sender_account_id=checking["id"],
                    amount="50.00",
                    category=TransactionCategory.GAMBLING,
                    description="Declined",
                    created_at=now - timedelta(days=1),
                    status=TransactionStatus.DECLINED,
                    mcc_code="7995",
                ),
            ]
        )
        db.commit()

    response = client.get(
        "/analytics/spending-summary?days=30",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["window_days"] == 30
    assert Decimal(str(data["total_spend"])) == Decimal("180.00")
    assert data["transaction_count"] == 2

    categories = {
        row["category"]: row
        for row in data["categories"]
    }

    assert Decimal(str(categories["Groceries"]["amount"])) == Decimal("120.00")
    assert Decimal(str(categories["Groceries"]["percentage"])) == Decimal("66.7")
    assert Decimal(str(categories["restaurants"]["amount"])) == Decimal("60.00")
    assert Decimal(str(categories["restaurants"]["percentage"])) == Decimal("33.3")

    assert [row["label"] for row in data["top_merchants"]] == [
        "REWE Munich",
        "L'Osteria",
    ]


def test_analytics_window_is_validated(
    client,
    auth_headers,
):
    too_small = client.get(
        "/analytics/spending-summary?days=0",
        headers=auth_headers,
    )
    too_large = client.get(
        "/analytics/customer-insights?days=366",
        headers=auth_headers,
    )

    assert too_small.status_code == 422
    assert too_large.status_code == 422


def test_customer_insights_generate_transparent_offer_rules(
    client,
    auth_headers,
):
    account = create_account(
        client,
        auth_headers,
        "checking",
        1000,
    )
    now = datetime.now(timezone.utc)

    with TestingSessionLocal() as db:
        db.add_all(
            [
                _transaction(
                    sender_account_id=account["id"],
                    amount="300.00",
                    category=TransactionCategory.GROCERIES,
                    description="REWE",
                    created_at=now - timedelta(days=1),
                ),
                _transaction(
                    sender_account_id=account["id"],
                    amount="100.00",
                    category=TransactionCategory.PUBLIC_TRANSIT,
                    description="DB Vertrieb GmbH",
                    created_at=now - timedelta(days=2),
                    mcc_code="4111",
                ),
                _transaction(
                    sender_account_id=account["id"],
                    amount="100.00",
                    category=TransactionCategory.INVESTMENTS,
                    description="Trade Republic",
                    created_at=now - timedelta(days=3),
                    mcc_code="6211",
                ),
            ]
        )
        db.commit()

    response = client.get(
        "/analytics/customer-insights?days=90",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert set(data["profile_tags"]) == {
        "grocery_focused",
        "mobility_spender",
        "financial_products_engaged",
    }
    assert Decimal(str(data["stability_category_share_percent"])) == Decimal("20.0")
    assert Decimal(str(data["risk_category_share_percent"])) == Decimal("0.0")

    offer_codes = {
        offer["code"]
        for offer in data["suggested_offers"]
    }
    assert offer_codes == {
        "grocery_cashback",
        "mobility_rewards",
        "financial_services_bundle",
    }


def test_elevated_risk_spending_is_a_signal_not_a_credit_offer(
    client,
    auth_headers,
):
    account = create_account(
        client,
        auth_headers,
        "checking",
        1000,
    )

    with TestingSessionLocal() as db:
        db.add(
            _transaction(
                sender_account_id=account["id"],
                amount="100.00",
                category=TransactionCategory.GAMBLING,
                description="Tipico",
                created_at=datetime.now(timezone.utc) - timedelta(days=1),
                mcc_code="7995",
            )
        )
        db.commit()

    response = client.get(
        "/analytics/customer-insights?days=90",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert "elevated_risk_category_spend" in data["profile_tags"]
    assert Decimal(str(data["risk_category_share_percent"])) == Decimal("100.0")
    assert data["suggested_offers"] == []


def test_new_user_gets_neutral_empty_analytics(
    client,
    auth_headers,
):
    summary = client.get(
        "/analytics/spending-summary",
        headers=auth_headers,
    )
    insights = client.get(
        "/analytics/customer-insights",
        headers=auth_headers,
    )

    assert summary.status_code == 200
    assert insights.status_code == 200

    assert Decimal(str(summary.json()["total_spend"])) == Decimal("0.00")
    assert summary.json()["transaction_count"] == 0
    assert summary.json()["categories"] == []
    assert summary.json()["top_merchants"] == []

    data = insights.json()
    assert data["profile_tags"] == []
    assert data["signals"] == []
    assert data["suggested_offers"] == []
