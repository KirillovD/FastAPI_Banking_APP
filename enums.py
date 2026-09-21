import enum


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
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    SERVICE_FEE = "service_fee"


class PaymentType(str, enum.Enum):
    POS = "pos"
    ONLINE = "online"


class TransactionCategory(str, enum.Enum):
    GROCERIES = "Groceries"
    RESTAURANTS = "restaurants"
    DELIVERY_FAST_FOOD = "delivery_fast_food"

    PUBLIC_TRANSIT = "public_transit"
    TAXI_CARSHARING = "taxi_carsharing"
    FUEL = "fuel"

    RENT = "rent"
    ELECTRICITY_WATER = "electricity_water"
    INTERNET_TV = "internet_tv"

    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    E_COMMERCE = "e_commerce"

    SUBSCRIPTIONS = "subscriptions"
    GAMING = "gaming"
    FITNESS = "fitness"

    INVESTMENTS = "investments"
    INSURANCES = "insurances"

    GAMBLING = "gambling"
    MICROLOANS = "microloans"

    SALARY = "salary"

    OTHER = "other"


class TransactionClassificationSource(str, enum.Enum):
    MCC = "mcc"
    MERCHANT_RULE = "merchant_rule"
    DESCRIPTION_RULE = "description_rule"
    SYSTEM = "system"
    FALLBACK = "fallback"


class CreditStatementStatus(str, enum.Enum):
    OPEN = "open"
    MINIMUM_PAID = "minimum_paid"
    PAID_IN_FULL = "paid_in_full"
    PAST_DUE = "past_due"
