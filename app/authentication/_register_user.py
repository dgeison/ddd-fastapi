from fastapi import Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.authentication._user import User
from app.authentication._user_repository import UserRepository, get_user_repository


class UserCreate(BaseModel):
    email: str
    password: str
    name: str


def register_user(
    body: UserCreate, user_repository: UserRepository = Depends(get_user_repository)
):
    if user_repository.get_by_email(body.email):
        return JSONResponse(
            status_code=400, content={"detail": "Email already registered"}
        )

    # Create a new user and save it to the database
    user = User(name=body.name, email=body.email, password=body.password)
    user_repository.create(user)

    return JSONResponse(
        status_code=201, content=None, headers={"Location": f"/users/{user.id}"}
    )
