from services.categorizer import categorizer

def test_categorizer_known_merchant():
    result = categorizer.categorize("REWE FILIALE 123")
    assert result["category"] == "Groceries"
    assert result["mcc_code"] == "5411"

def test_categorizer_unknown_merchant():
    result = categorizer.categorize("restaurant bill at friday")
    assert result["category"] == "Uncategorized"