from sqlalchemy.orm import Session
from fastapi.params import Depends
from app.infra.database import get_db
from app.subscription.plan._plan import Plan


class PlanRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, plan_id: int):
        return self.db.query(Plan).filter(Plan.id == plan_id).first()


def get_plan_repository(db: Session = Depends(get_db)) -> PlanRepository:
    """
    Dependency to get a PlanRepository instance.
    """
    return PlanRepository(db)
