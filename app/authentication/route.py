from fastapi import APIRouter

from app.authentication._register_user import register_user
from app.authentication._create_token import create_token
from app.authentication._get_user_profile import UserProfileResponse, get_user_profile

user_router = APIRouter()

user_router.add_api_route(
    "/",
    endpoint=register_user,
    methods=["POST"],
    response_model=None,
    tags=["users"],
    summary="Create a new user",
)


user_router.add_api_route(
    "/token",
    endpoint=create_token,
    methods=["POST"],
    response_model=None,
    tags=["users"],
    summary="Create a JWT token for user authentication",
)

user_router.add_api_route(
    "/profile",
    endpoint=get_user_profile,
    methods=["GET"],
    response_model=UserProfileResponse,
    tags=["users"],
    summary="Get the profile of the authenticated user",
)
