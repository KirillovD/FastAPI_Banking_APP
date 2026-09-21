from enums import (
    TransactionCategory,
    TransactionClassificationSource,
)
from mock_data_generator.generate_data import TRANSACTION_PATTERNS


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


class TransactionCategorizer:
    def __init__(self):
        self.mcc_rules: dict[str, TransactionCategory] = {}
        self.description_rules: dict[str, TransactionCategory] = {}

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
                    keyword = merchant.split()[0].casefold()
                    self.description_rules[keyword] = category

    def categorize(
        self,
        raw_description: str | None = None,
        *,
        mcc_code: str | None = None,
        rule_source: TransactionClassificationSource = (
            TransactionClassificationSource.DESCRIPTION_RULE
        ),
    ) -> dict:
        normalized_mcc = str(mcc_code) if mcc_code else None

        if normalized_mcc in self.mcc_rules:
            return {
                "category": self.mcc_rules[normalized_mcc],
                "mcc_code": normalized_mcc,
                "classification_source": TransactionClassificationSource.MCC,
            }

        clean_description = (
            raw_description.casefold()
            if raw_description
            else ""
        )

        for keyword, category in self.description_rules.items():
            if keyword in clean_description:
                return {
                    "category": category,
                    "mcc_code": normalized_mcc,
                    "classification_source": rule_source,
                }

        return {
            "category": TransactionCategory.OTHER,
            "mcc_code": normalized_mcc,
            "classification_source": TransactionClassificationSource.FALLBACK,
        }


categorizer = TransactionCategorizer()
