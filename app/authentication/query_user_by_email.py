from fastapi.params import Depends
from sqlalchemy.orm import Session

from app.authentication._user_repository import UserRepository
from app.infra.database import get_db


class UserByEmailResult:
    def __init__(self, id: int, name: str, email: str):
        self.id = id
        self.name = name
        self.email = email


class QueryUserByEmail:
    user_repository: UserRepository

    def __init__(self, db: Session):
        self.user_repository = UserRepository(db)

    def execute(self, email: str) -> UserByEmailResult | None:
        user = self.user_repository.get_by_email(email)
        if not user:
            return None
        return UserByEmailResult(id=user.id, name=user.name, email=user.email)


def get_query_user_by_email(db: Session = Depends(get_db)) -> QueryUserByEmail | None:
    return QueryUserByEmail(db)
