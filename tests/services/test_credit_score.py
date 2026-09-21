from datetime import datetime, timedelta, timezone
from decimal import Decimal

from services import credit_score


def test_payment_history_has_no_impact_without_history():
    factor = credit_score._payment_history_factor(0, 0)

    assert factor.impact == 0


def test_payment_history_rewards_established_on_time_history():
    factor = credit_score._payment_history_factor(6, 0)

    assert factor.impact == 120


def test_payment_history_penalizes_established_missed_history():
    factor = credit_score._payment_history_factor(0, 6)

    assert factor.impact == -120


def test_payment_history_confidence_grows_with_history():
    one_statement = credit_score._payment_history_factor(1, 0)
    six_statements = credit_score._payment_history_factor(6, 0)

    assert one_statement.impact == 20
    assert six_statements.impact == 120


def test_delinquency_combines_current_and_historical_severity():
    factor = credit_score._delinquency_factor(
        current_dpd=10,
        max_dpd=30,
    )

    assert factor.impact == -80


def test_delinquency_is_capped():
    factor = credit_score._delinquency_factor(
        current_dpd=100,
        max_dpd=100,
    )

    assert factor.impact == -150


def test_utilization_factor_bands():
    assert (
        credit_score._utilization_factor(
            Decimal("0"),
            Decimal("500"),
        ).impact
        == 0
    )
    assert (
        credit_score._utilization_factor(
            Decimal("100"),
            Decimal("500"),
        ).impact
        == 40
    )
    assert (
        credit_score._utilization_factor(
            Decimal("300"),
            Decimal("500"),
        ).impact
        == -20
    )
    assert (
        credit_score._utilization_factor(
            Decimal("450"),
            Decimal("500"),
        ).impact
        == -60
    )


def test_credit_age_is_modest_and_bounded():
    now = datetime(2026, 9, 21, tzinfo=timezone.utc)

    new_account = credit_score._credit_age_factor(
        now - timedelta(days=10),
        now,
    )
    old_account = credit_score._credit_age_factor(
        now - timedelta(days=1500),
        now,
    )

    assert new_account.impact == 0
    assert old_account.impact == 40


def test_rapid_depletion_penalty_is_capped():
    assert credit_score._rapid_depletion_factor(2).impact == -20
    assert credit_score._rapid_depletion_factor(20).impact == -60



def test_single_missed_obligation_is_immediate_penalty():
    factor = credit_score._payment_history_factor(0, 1)

    assert factor.impact == -50


def test_score_clamp_respects_declared_range():
    assert credit_score._clamp(100, 300, 850) == 300
    assert credit_score._clamp(900, 300, 850) == 850
    assert credit_score._clamp(600, 300, 850) == 600
