from fastapi import Depends
from pydantic import BaseModel

from app.authentication import get_email_from_token
from app.subscription.user._user_repository import UserRepository, get_user_repository


class PlanResponse(BaseModel):
    id: int
    name: str
    price: float
    active: bool
    is_free: bool


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    plans: list[PlanResponse] = []


async def get_user(
    email: str = Depends(get_email_from_token),
    user_repository: UserRepository = Depends(get_user_repository),
) -> UserResponse:
    user = user_repository.get_by_email(email)
    if not user:
        return None

    plans = [
        PlanResponse(
            id=up.plan.id,
            name=up.plan.name,
            price=up.plan.price,
            active=up.active,
            is_free=up.plan.is_free,
        )
        for up in user.user_plans
    ]

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        plans=plans,
    )
