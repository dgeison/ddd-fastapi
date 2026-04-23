from fastapi import APIRouter

from app.movement.bank._register_bank_account import register_bank_account

movement_router = APIRouter()

movement_router.add_api_route(
    "/bank-accounts",
    endpoint=register_bank_account,
    methods=["POST"],
    response_model=None,
    tags=["movement"],
    summary="Register a new bank account for the user",
)
