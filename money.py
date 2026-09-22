from decimal import Decimal, InvalidOperation
from typing import Annotated

from pydantic import AfterValidator


MONEY_QUANTUM = Decimal("0.01")
MAX_MONEY = Decimal("9999999999.99")
MIN_MONEY = -MAX_MONEY


def normalize_money(
    value: Decimal,
    *,
    positive: bool = False,
) -> Decimal:
    amount = Decimal(value)

    if not amount.is_finite():
        raise ValueError("Money value must be finite")

    if amount < MIN_MONEY or amount > MAX_MONEY:
        raise ValueError(
            f"Money value must be between {MIN_MONEY} and {MAX_MONEY}"
        )

    try:
        normalized = amount.quantize(MONEY_QUANTUM)
    except InvalidOperation as exc:
        raise ValueError("Money value is outside the supported range") from exc

    if normalized != amount:
        raise ValueError("Money values support at most two decimal places")

    if positive and normalized <= Decimal("0.00"):
        raise ValueError("Amount must be greater than zero")

    return normalized


def validate_money(value: Decimal) -> Decimal:
    return normalize_money(value)


def validate_positive_money(value: Decimal) -> Decimal:
    return normalize_money(value, positive=True)


Money = Annotated[Decimal, AfterValidator(validate_money)]
PositiveMoney = Annotated[
    Decimal,
    AfterValidator(validate_positive_money),
]
