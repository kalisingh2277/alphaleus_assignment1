"""Argus API entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import changes, competitors, pipeline, profile
from app.core.config import settings
from app.core.database import init_db
from app.scheduler import shutdown_scheduler, start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    if settings.enable_scheduler:
        start_scheduler()
    yield
    shutdown_scheduler()


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
app.include_router(changes.router, prefix="/api/v1")
app.include_router(pipeline.router, prefix="/api/v1")
app.include_router(profile.router, prefix="/api/v1")
