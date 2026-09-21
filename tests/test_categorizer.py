from enums import (
    TransactionCategory,
    TransactionClassificationSource,
)
from services.categorizer import categorizer


def test_categorizer_prefers_known_mcc_over_description():
    result = categorizer.categorize(
        "Tipico",
        mcc_code="5411",
        rule_source=TransactionClassificationSource.MERCHANT_RULE,
    )

    assert result["category"] == TransactionCategory.GROCERIES
    assert result["mcc_code"] == "5411"
    assert (
        result["classification_source"]
        == TransactionClassificationSource.MCC
    )


def test_categorizer_uses_merchant_rule_for_unknown_mcc():
    result = categorizer.categorize(
        "REWE FILIALE 123",
        mcc_code="9999",
        rule_source=TransactionClassificationSource.MERCHANT_RULE,
    )

    assert result["category"] == TransactionCategory.GROCERIES
    assert result["mcc_code"] == "9999"
    assert (
        result["classification_source"]
        == TransactionClassificationSource.MERCHANT_RULE
    )


def test_categorizer_uses_description_rule_without_mcc():
    result = categorizer.categorize(
        "REWE FILIALE 123",
        rule_source=TransactionClassificationSource.DESCRIPTION_RULE,
    )

    assert result["category"] == TransactionCategory.GROCERIES
    assert result["mcc_code"] is None
    assert (
        result["classification_source"]
        == TransactionClassificationSource.DESCRIPTION_RULE
    )


def test_categorizer_unknown_transaction_uses_other():
    result = categorizer.categorize("completely unknown description")

    assert result["category"] == TransactionCategory.OTHER
    assert result["mcc_code"] is None
    assert (
        result["classification_source"]
        == TransactionClassificationSource.FALLBACK
    )
