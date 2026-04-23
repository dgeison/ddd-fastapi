import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.authentication import user_router
from app.domain_exception import DomainException
from app.infra.database import init_database, create_tables
from app.subscription import subscription_router
from app.movement import movement_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
init_database()
create_tables()


app = FastAPI(
    title="Track Money API",
    description="API for tracking money and expenses",
    version="1.0.0",
)

app.include_router(
    user_router,
    prefix="/users",
    tags=["users"],
)


@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    logger.info(f"Registering DomainException handler: {exc.message}")
    return JSONResponse(
        status_code=400,
        content={"detail": exc.message},
    )


@app.get("/health")
async def health_check():
    return JSONResponse({"status": "healthy"})


app.include_router(
    subscription_router,
    prefix="/subscriptions",
)

app.include_router(
    movement_router,
    prefix="/movements",
)



def main():
    print("Hello from track-money!")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
