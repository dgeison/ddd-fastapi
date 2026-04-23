from fastapi import Depends
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.authentication._user_repository import UserRepository, get_user_repository
from app.authentication._auth import generate_jwt_token


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


async def create_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_repository: UserRepository = Depends(get_user_repository),
) -> TokenResponse:
    user = user_repository.get_by_email(form_data.username)
    if not user:
        return JSONResponse(status_code=401, content={"detail": "Invalid credentials"})
    if not user.verify_password(form_data.password):
        return JSONResponse(status_code=401, content={"detail": "Invalid credentials"})

    token = generate_jwt_token(user)
    return TokenResponse(access_token=token, token_type="bearer")
