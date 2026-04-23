from fastapi import APIRouter
from app.subscription.user._select_plan import select_plan
from app.subscription.user._get_user import get_user


subscription_router = APIRouter()

subscription_router.add_api_route(
    "/select-plan",
    endpoint=select_plan,
    methods=["POST"],
    response_model=None,
    tags=["subscription"],
    summary="Select a subscription plan for the user",
)


subscription_router.add_api_route(
    "/user",
    endpoint=get_user,
    methods=["GET"],
    response_model=None,
    tags=["subscription"],
    summary="Get the current user's subscription details",
)
