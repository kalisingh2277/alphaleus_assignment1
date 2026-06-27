"""Argus API entrypoint."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.v1 import changes, competitors, digest, pipeline, profile
from app.core.config import settings
from app.core.database import init_db
from app.scheduler import shutdown_scheduler, start_scheduler

# Where the built frontend lives (single-service deploy). Overridable for Docker.
_FRONTEND_DIST = Path(
    os.environ.get("FRONTEND_DIST")
    or Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
)


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
app.include_router(digest.router, prefix="/api/v1")


# Serve the built single-page app (and let client-side routes fall back to
# index.html). Only active when a build exists; in dev, Vite serves the frontend.
if _FRONTEND_DIST.is_dir():

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse:
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = _FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_FRONTEND_DIST / "index.html")
