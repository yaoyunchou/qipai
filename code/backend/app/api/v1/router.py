from fastapi import APIRouter

from app.api.v1 import (
    auth,
    companion_loans,
    config,
    expenses,
    loans,
    orders,
    play_companion,
    reports,
    tables,
    users,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(tables.router)
api_router.include_router(orders.router)
api_router.include_router(config.router)
api_router.include_router(reports.router)
api_router.include_router(expenses.router)
api_router.include_router(play_companion.router)
api_router.include_router(companion_loans.router)
api_router.include_router(loans.router)
