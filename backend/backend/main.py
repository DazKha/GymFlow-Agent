from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import SessionLocal, engine
from .models import Base
from .routers.bookings import router as bookings_router
from .routers.clubs import router as clubs_router
from .routers.facilities import router as facilities_router
from .routers.memberships import router as memberships_router
from .seed import seed_data


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="GymFlow Backend",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(memberships_router)
app.include_router(clubs_router)
app.include_router(facilities_router)
app.include_router(bookings_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
