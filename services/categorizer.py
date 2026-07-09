# categorizer.py

from ai_model.generate_data import TRANSACTION_PATTERNS


class TransactionCategorizer:
    def __init__(self):
        #dict will be filled with {merchant name : [subcat, merchant code]}
        self.rules = {}

        for category, subcategories in TRANSACTION_PATTERNS.items():
            for sub_name, data in subcategories.items():
                for merchant in data["merchants"]:
                    # We only take the merchan's name ("REWE FIL. {city}" to "rewe")
                    # turn into lowercase for easier search
                    base_word = merchant.split()[0].lower()
                    self.rules[base_word] = (sub_name, data["mcc"])

    def categorize(self, raw_description: str) -> dict:

        #check if description is empty
        if not raw_description:
            return {"category": "Other", "mcc": "0000"}

        # lowercase for easier comparison
        clean_desc = raw_description.lower()

        # Search for the merchant names from the rules dict
        #then assign the category if we find them
        for keyword, (category, mcc) in self.rules.items():
            if keyword in clean_desc:
                return {
                    "category": category,
                    "mcc_code": mcc
                }

        # Set to default if nothing is found
        return {
            "category": "Uncategorized",
            "mcc_code": "0000"
        }


# Create singleton, so we don't have to create a new dict every time
categorizer = TransactionCategorizer()