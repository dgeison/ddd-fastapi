from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.subscription.plan._plan import Plan
from sqlalchemy import DateTime as Datetime

from app.infra.database import Base


class UserPlan(Base):
    __tablename__ = "user_plans"
    __table_args__ = {"schema": "subscription"}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("subscription.users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey(Plan.id), nullable=False)
    active = Column(Boolean, nullable=False, default=False)
    # simulação de cartao de credito, na vida real é mais complexo
    credit_card = Column(String(24), nullable=True)
    created_at = Column(Datetime, nullable=False)

    user = relationship("app.subscription.user._user.User", back_populates="user_plans")
    plan = relationship(Plan)

    def __init__(
        self,
        plan: Plan,
        active: bool,
        credit_card: str | None,
    ):
        self.plan = plan
        self.active = active
        self.credit_card = credit_card
        self.created_at = datetime.now(timezone.utc)
