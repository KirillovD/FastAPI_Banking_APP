import re

from enums import (
    TransactionCategory,
    TransactionClassificationSource,
)
from mock_data_generator.patterns import TRANSACTION_PATTERNS


CATEGORY_LABELS = {
    "Groceries": TransactionCategory.GROCERIES,
    "Restaurants": TransactionCategory.RESTAURANTS,
    "Delivery & Fast Food": TransactionCategory.DELIVERY_FAST_FOOD,
    "Public Transit": TransactionCategory.PUBLIC_TRANSIT,
    "Taxi & Carsharing": TransactionCategory.TAXI_CARSHARING,
    "Fuel": TransactionCategory.FUEL,
    "Rent": TransactionCategory.RENT,
    "Electricity & Water": TransactionCategory.ELECTRICITY_WATER,
    "Internet & TV": TransactionCategory.INTERNET_TV,
    "Electronics": TransactionCategory.ELECTRONICS,
    "Clothing": TransactionCategory.CLOTHING,
    "E-commerce": TransactionCategory.E_COMMERCE,
    "Subscriptions": TransactionCategory.SUBSCRIPTIONS,
    "Gaming": TransactionCategory.GAMING,
    "Fitness": TransactionCategory.FITNESS,
    "Investments": TransactionCategory.INVESTMENTS,
    "Insurances": TransactionCategory.INSURANCES,
    "Gambling": TransactionCategory.GAMBLING,
    "Microloans": TransactionCategory.MICROLOANS,
    "Salary": TransactionCategory.SALARY,
}


SAFE_ALIASES = {
    "rewe": TransactionCategory.GROCERIES,
    "edeka": TransactionCategory.GROCERIES,
    "aldi sued": TransactionCategory.GROCERIES,
    "aldi süd": TransactionCategory.GROCERIES,
    "kaufland": TransactionCategory.GROCERIES,
    "lidl": TransactionCategory.GROCERIES,
    "alnatura": TransactionCategory.GROCERIES,
    "lieferando": TransactionCategory.DELIVERY_FAST_FOOD,
    "mcdonalds": TransactionCategory.DELIVERY_FAST_FOOD,
    "burger king": TransactionCategory.DELIVERY_FAST_FOOD,
    "freenow": TransactionCategory.TAXI_CARSHARING,
    "mediamarkt": TransactionCategory.ELECTRONICS,
    "saturn": TransactionCategory.ELECTRONICS,
    "zalando": TransactionCategory.CLOTHING,
    "amazon": TransactionCategory.E_COMMERCE,
    "netflix": TransactionCategory.SUBSCRIPTIONS,
    "spotify": TransactionCategory.SUBSCRIPTIONS,
    "tipico": TransactionCategory.GAMBLING,
    "bwin": TransactionCategory.GAMBLING,
    "tipwin": TransactionCategory.GAMBLING,
    "klarna": TransactionCategory.MICROLOANS,
    "ferratum": TransactionCategory.MICROLOANS,
    "cashper": TransactionCategory.MICROLOANS,
}


def _normalize_text(value: str) -> str:
    value = re.sub(
        r"\{[^}]+\}",
        " ",
        value.casefold(),
    )
    value = re.sub(
        r"[^\w]+",
        " ",
        value,
        flags=re.UNICODE,
    )
    return " ".join(value.split())


class TransactionCategorizer:
    def __init__(self):
        self.mcc_rules: dict[
            str,
            TransactionCategory,
        ] = {}
        description_rules: dict[
            str,
            TransactionCategory,
        ] = {}

        for subcategories in TRANSACTION_PATTERNS.values():
            for sub_name, data in subcategories.items():
                category = CATEGORY_LABELS.get(
                    sub_name,
                    TransactionCategory.OTHER,
                )
                mcc = data.get("mcc")

                if mcc:
                    self.mcc_rules[str(mcc)] = category

                for merchant in data["merchants"]:
                    phrase = _normalize_text(merchant)

                    if phrase:
                        description_rules[phrase] = category

        description_rules.update(SAFE_ALIASES)

        self.description_rules = sorted(
            description_rules.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        )

    def categorize(
        self,
        raw_description: str | None = None,
        *,
        mcc_code: str | None = None,
        rule_source: TransactionClassificationSource = (
            TransactionClassificationSource.DESCRIPTION_RULE
        ),
    ) -> dict:
        normalized_mcc = (
            str(mcc_code)
            if mcc_code
            else None
        )

        if normalized_mcc in self.mcc_rules:
            return {
                "category": self.mcc_rules[normalized_mcc],
                "mcc_code": normalized_mcc,
                "classification_source": (
                    TransactionClassificationSource.MCC
                ),
            }

        clean_description = _normalize_text(
            raw_description or ""
        )

        for phrase, category in self.description_rules:
            if phrase in clean_description:
                return {
                    "category": category,
                    "mcc_code": normalized_mcc,
                    "classification_source": rule_source,
                }

        return {
            "category": TransactionCategory.OTHER,
            "mcc_code": normalized_mcc,
            "classification_source": (
                TransactionClassificationSource.FALLBACK
            ),
        }


categorizer = TransactionCategorizer()
