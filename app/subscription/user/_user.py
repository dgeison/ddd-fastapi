from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.domain_exception import DomainException
from app.subscription.plan._plan import Plan
from app.infra.database import Base
from app.subscription.user._user_plan import UserPlan


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "subscription"}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    email = Column(String(128), unique=True, index=True, nullable=False)

    user_plans = relationship("UserPlan", back_populates="user")

    def __init__(self, name: str, email: str):
        DomainException.validate(
            name and len(name) <= 128, "Name must be between 1 and 128 characters."
        )
        self.name = name
        DomainException.validate(
            email and len(email) <= 128, "Email must be between 1 and 128 characters."
        )
        self.email = email

    def add_plan(self, plan: Plan, credit_card: str = None):
        DomainException.validate(plan is not None, "Plan must be provided.")

        if not plan.is_free:
            DomainException.validate(
                credit_card,
                "Credit card information must be provided for inactive plans.",
            )

        self._deactivate_plans()
        user_plan = UserPlan(plan=plan, active=True, credit_card=credit_card)
        self.user_plans.append(user_plan)

    def _deactivate_plans(self):
        for user_plan in self.user_plans:
            user_plan.active = False

    def get_active_plan(self) -> Plan | None:
        for user_plan in self.user_plans:
            if user_plan.active:
                return user_plan.plan
        return None
