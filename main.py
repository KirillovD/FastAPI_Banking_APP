from fastapi import FastAPI, APIRouter
from router import users
app = FastAPI()

app.include_router(users.router)