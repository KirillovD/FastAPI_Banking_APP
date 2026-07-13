import enum
from sqlalchemy import Enum as SQLEnum


class AccountType(str, enum.Enum):
    CHECKING = "checking"
    CREDIT = "credit"
    SAVINGS = "savings"

class TransactionStatus(str, enum.Enum):
    SUCCESSFUL = "successful"
    DECLINED = "declined"
    PROCESSING = "processing"

class OperationType(str, enum.Enum):
    TRANSFER = "transfer"
    PAYMENT = "payment"
    SERVICE_FEE = "service_fee"

class PaymentType(str, enum.Enum):
    POS = "pos"
    ONLINE = "online"

class TransactionCategory(str, enum.Enum):
    # Food & Dining
    GROCERIES = "Groceries"
    RESTAURANTS = "restaurants"
    DELIVERY_FAST_FOOD = "delivery_fast_food"

    # Transport & Auto
    PUBLIC_TRANSIT = "public_transit"
    TAXI_CARSHARING = "taxi_carsharing"
    FUEL = "fuel"

    # Housing & Utilities
    RENT = "rent"
    ELECTRICITY_WATER = "electricity_water"
    INTERNET_TV = "internet_tv"

    # Shopping
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    E_COMMERCE = "e_commerce"

    # Entertainment & Lifestyle
    SUBSCRIPTIONS = "subscriptions"
    GAMING = "gaming"
    FITNESS = "fitness"

    # Financial (Score Boosters)
    INVESTMENTS = "investments"
    INSURANCES = "insurances"

    # High Risk (Score Killers)
    GAMBLING = "gambling"
    MICROLOANS = "microloans"

    # Income
    SALARY = "salary"

    # Фолбэк на всякий случай
    OTHER = "other"


