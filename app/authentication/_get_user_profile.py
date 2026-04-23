from fastapi.params import Depends
from pydantic import BaseModel
from app.authentication.get_email_from_token import get_email_from_token
from app.authentication._user_repository import get_user_repository


class UserProfileResponse(BaseModel):
    name: str
    email: str

    class Config:
        from_attributes = True


async def get_user_profile(
    email: str = Depends(get_email_from_token),
    user_repository=Depends(get_user_repository),
) -> UserProfileResponse:
    user = user_repository.get_by_email(email)
    return user
