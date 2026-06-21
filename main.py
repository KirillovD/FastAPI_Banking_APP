from fastapi import FastAPI, APIRouter
from router import users, accounts, auth

app = FastAPI()

app.include_router(users.router)
app.include_router(accounts.router)
app.include_router(auth.router)