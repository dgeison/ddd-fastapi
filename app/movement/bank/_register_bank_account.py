from fastapi import Depends, HTTPException
from pydantic import BaseModel

from app.authentication.get_email_from_token import get_email_from_token
from app.authentication.query_user_by_email import (
    QueryUserByEmail,
    get_query_user_by_email,
)
from app.movement.bank._bank_account import BankAccount, User
from app.movement.bank._bank_account_repository import (
    BankAccountRepository,
    get_bank_account_repository,
)
from app.subscription import QueryUserPlan, get_query_user_plan


class BankAccountCreate(BaseModel):
    name: str
    bank_name: str
    account_number: str
    initial_balance: float = 0.0


async def register_bank_account(
    body: BankAccountCreate,
    email: str = Depends(get_email_from_token),
    bank_account_repository: BankAccountRepository = Depends(
        get_bank_account_repository
    ),
    query_user_by_email: QueryUserByEmail = Depends(get_query_user_by_email),
    query_user_plan: QueryUserPlan = Depends(get_query_user_plan),
) -> None:
    user_plan = query_user_plan.execute(email)
    if not user_plan:
        raise HTTPException(status_code=400, detail="User has no active plan")
    bank_accounts = bank_account_repository.get_all_by_user(email)
    if len(bank_accounts) >= user_plan.max_number_accounts:
        raise HTTPException(
            status_code=400,
            detail="User has reached the maximum number of bank accounts for their plan",
        )

    user_auth = query_user_by_email.execute(email)
    user = User(name=user_auth.name, email=user_auth.email)
    bank_account = BankAccount(
        name=body.name,
        bank_name=body.bank_name,
        account_number=body.account_number,
        user=user,
        balance=body.initial_balance,
    )
    bank_account_repository.create(bank_account)
