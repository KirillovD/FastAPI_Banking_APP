TRANSACTION_PATTERNS = {
    "Food & Dining": {
        "Groceries": {"mcc": "5411",
                      "merchants": ["REWE FIL. {city}", "EDEKA {city}", "ALDI SUED", "Kaufland", "Lidl", "Alnatura"],
                      "amount": (15, 150), "weight": 40},
        "Restaurants": {"mcc": "5812", "merchants": ["L'Osteria", "Block House", "Vapiano", "Local Cafe {city}"],
                        "amount": (30, 120), "weight": 10},
        "Delivery & Fast Food": {"mcc": "5814", "merchants": ["Uber Eats", "Lieferando", "McDonalds", "Burger King"],
                                 "amount": (15, 45), "weight": 20},
    },

    "Transport & Auto": {
        "Public Transit": {"mcc": "4111",
                           "merchants": ["DB Vertrieb GmbH", "BVG Ticket", "Deutschlandticket", "MVG Automaten"],
                           "amount": (3, 55), "weight": 20},
        "Taxi & Carsharing": {"mcc": "4121", "merchants": ["Uber BV", "FREENOW", "Miles Mobility", "ShareNow"],
                              "amount": (10, 40), "weight": 15},
        "Fuel": {"mcc": "5541", "merchants": ["ARAL Tankstelle", "Shell", "TotalEnergies", "Esso"], "amount": (40, 100),
                 "weight": 15},
    },

    "Housing & Utilities": {
        "Rent": {"mcc": "6513", "merchants": ["Miete WG {city}", "Vonovia SE", "Heimstaden"], "amount": (500, 1600),
                 "weight": 5},
        "Electricity & Water": {"mcc": "4900", "merchants": ["Vattenfall Europe", "E.ON", "Stadtwerke {city}"],
                                "amount": (50, 150), "weight": 5},
        "Internet & TV": {"mcc": "4814", "merchants": ["Vodafone GmbH", "Telekom Deutschland", "O2 Telefonica",
                                                       "Rundfunkbeitrag ARD ZDF"], "amount": (18, 60), "weight": 5},
    },

    "Shopping": {
        "Electronics": {"mcc": "5732", "merchants": ["MediaMarkt", "Saturn", "Apple Store", "Cyberport"],
                        "amount": (50, 1200), "weight": 5},
        "Clothing": {"mcc": "5651", "merchants": ["Zalando SE", "H&M", "Zara", "ASOS"], "amount": (30, 250),
                     "weight": 15},
        "E-commerce": {"mcc": "5399", "merchants": ["Amazon.de", "eBay", "AliExpress"], "amount": (10, 300),
                       "weight": 25},
    },

    "Entertainment & Lifestyle": {
        "Subscriptions": {"mcc": "5815", "merchants": ["Netflix", "Spotify AB", "Amazon Prime", "YouTube Premium"],
                          "amount": (10, 18), "weight": 10},
        "Gaming": {"mcc": "7994", "merchants": ["Steam Games", "PlayStation Network", "Nintendo"], "amount": (5, 70),
                   "weight": 10},
        "Fitness": {"mcc": "7997", "merchants": ["McFIT", "FitX", "Urban Sports Club", "John Reed"], "amount": (25, 70),
                    "weight": 5},
    },

    "Financial (Score Boosters)": {
        "Investments": {"mcc": "6211", "merchants": ["Trade Republic", "Scalable Capital", "DKB Broker"],
                        "amount": (50, 500), "weight": 5},
        "Insurances": {"mcc": "6300", "merchants": ["TK Gesundheit", "Allianz SE", "HUK-Coburg", "Clark"],
                       "amount": (30, 150), "weight": 5},
    },

    "High Risk (Score Killers)": {
        "Gambling": {"mcc": "7995", "merchants": ["Tipico", "Bwin", "Tipwin", "Online Casino"], "amount": (10, 200),
                     "weight": 2},  # Низкий weight, чтобы не спамить, но маркер важный
        "Microloans": {"mcc": "6012", "merchants": ["Klarna Bank AB", "Ferratum", "Cashper"], "amount": (50, 300),
                       "weight": 3},
    },

    "Income": {
        "Salary": {"mcc": None, "merchants": ["Gehalt {month}", "Lohnabrechnung", "Arbeitgeber GmbH"],
                   "amount": (2500, 5000), "weight": 2},
    }
}
