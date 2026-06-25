from fastapi import FastAPI
from router import users, accounts, auth, transactions, admin

app = FastAPI()

app.include_router(users.router)
app.include_router(accounts.router)
app.include_router(auth.router)

app.include_router(transactions.router)

app.include_router(admin.router)