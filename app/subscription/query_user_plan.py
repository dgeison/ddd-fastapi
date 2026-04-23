from fastapi import Depends
from sqlalchemy.orm import Session

from app.infra.database import get_db
from app.subscription.user._user_repository import UserRepository


class UserPlanResult:
    def __init__(self, plan_id: int, plan_name: str, max_number_accounts: int):
        self.plan_id = plan_id
        self.plan_name = plan_name
        self.max_number_accounts = max_number_accounts


class QueryUserPlan:
    user_repository: UserRepository

    def __init__(self, db: Session):
        self.user_repository = UserRepository(db)

    def execute(self, email: str) -> UserPlanResult | None:
        result = self.user_repository.get_by_email(email)
        if not result:
            return None
        plan_active = result.get_active_plan()
        if not plan_active:
            return None

        return UserPlanResult(
            plan_id=plan_active.id,
            plan_name=plan_active.name,
            max_number_accounts=plan_active.max_number_accounts,
        )


def get_query_user_plan(db: Session = Depends(get_db)) -> QueryUserPlan | None:
    return QueryUserPlan(db)
