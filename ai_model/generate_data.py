import csv
import random
from faker import Faker

fake = Faker("de_De")

CATEGORIES_MAP = {
    "Groceries": [
        "REWE FIL. {city}", "EDEKA {city}", "ALDI SUED",
        "Lidl", "Kaufland", "Netto Marken-Discount", "Alnatura"
    ],
    "Transport": [
        "DB Vertrieb GmbH", "BVG Ticket", "ARAL Tankstelle",
        "Shell", "Uber BV", "Tier Mobility", "Deutschlandticket"
    ],
    "Housing": [
        "Miete WG {city}", "Stromrechnung Vattenfall",
        "Rundfunkbeitrag ARD ZDF", "Vodafone Internet", "O2 DSL"
    ],
    "Entertainment": [
        "Netflix", "Spotify AB", "CinemaxX",
        "Steam Games", "Amazon Prime", "Eventim Ticket"
    ],
    "Income": [
        "Gehalt {month}", "Lohnabrechnung", "Steuerrueckerstattung"
    ],
    "Travel" : [],
    "Restaurants" : [],
    "Food delivery" : [],
    

}