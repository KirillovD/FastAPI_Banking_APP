from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from database import SessionLocal, init_db
from mock_data_generator.seed_demo import seed_demo_data
from router import (
    accounts,
    admin,
    analytics,
    auth,
    cards,
    credit_accounts,
    credit_score,
    payments,
    transactions,
    users,
)


FRONTEND_DIST = Path(__file__).resolve().parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_schema:
        init_db()

    if settings.seed_demo_data:
        with SessionLocal() as db:
            seed_demo_data(
                db,
                password=settings.demo_user_password or "",
            )

    yield


app = FastAPI(
    title="FastAPI Banking Simulator",
    version="0.3.0",
    description=(
        "Portfolio banking simulator with payments, statements, "
        "transaction intelligence and a synthetic credit score."
    ),
    lifespan=lifespan,
)


@app.get("/health", tags=["Operations"])
def health_check():
    return {"status": "ok"}


app.include_router(users.router)
app.include_router(accounts.router)
app.include_router(analytics.router)
app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(payments.router)
app.include_router(credit_accounts.router)
app.include_router(credit_score.router)
app.include_router(admin.router)
app.include_router(cards.router)


if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=assets_dir),
            name="frontend-assets",
        )

    @app.get("/", include_in_schema=False)
    def frontend_index():
        return FileResponse(
            FRONTEND_DIST / "index.html"
        )
