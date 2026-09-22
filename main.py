from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import settings
from database import init_db
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_schema:
        init_db()
    yield


app = FastAPI(
    title="FastAPI Banking Simulator",
    version="0.2.0",
    description=(
        "Portfolio banking simulator with payments, statements, "
        "transaction intelligence and a synthetic credit score."
    ),
    lifespan=lifespan,
)

app.include_router(users.router)
app.include_router(accounts.router)
app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(payments.router)
app.include_router(credit_accounts.router)
app.include_router(credit_score.router)
app.include_router(admin.router)
app.include_router(cards.router)
