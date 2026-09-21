from fastapi import FastAPI
from router import (
    accounts,
    admin,
    auth,
    cards,
    credit_accounts,
    credit_score,
    payments,
    transactions,
    users,
)


app = FastAPI()

app.include_router(users.router)
app.include_router(accounts.router)
app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(payments.router)
app.include_router(credit_accounts.router)
app.include_router(credit_score.router)
app.include_router(admin.router)
app.include_router(cards.router)
