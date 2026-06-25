"""Argus API entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import competitors
from app.core.config import settings
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title=f"{settings.app_name} API", version="0.1.0", lifespan=lifespan)

# Wide-open CORS for now; locked down to the real frontend origin before deploy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}


app.include_router(competitors.router, prefix="/api/v1")
