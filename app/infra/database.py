import os

from sqlalchemy import Engine, text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


Base = declarative_base()

_engine: Engine | None = None
_sessionLocal: sessionmaker | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        if not os.getenv("DATABASE_URL"):
            raise ValueError("DATABASE_URL environment variable is not set")
        _engine = create_engine(os.getenv("DATABASE_URL"))
    return _engine


def get_session_local() -> sessionmaker:
    global _sessionLocal
    if _sessionLocal is None:
        _sessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=get_engine()
        )
    return _sessionLocal


def get_db():
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database():
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS authentication"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS subscription"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS movement"))
        conn.commit()


def create_tables():
    engine = get_engine()
    from app.authentication._user import (
        User,  # noqa: F401 - Import required for SQLAlchemy model discovery
    )
    
    from app.movement.bank._bank_account import (
        BankAccount,  # noqa: F401 - Import required for SQLAlchemy model discovery
    )

    from app.subscription.plan._plan import (
        Plan,  # noqa: F401 - Import required for SQLAlchemy model discovery
    )

    from app.subscription.user._user_plan import (
        UserPlan,  # noqa: F401 - Import required for SQLAlchemy model discovery
    )


    Base.metadata.create_all(bind=engine)
