"""Pipeline control endpoint — manually trigger a full scrape/detect run."""

from fastapi import APIRouter

from app.pipeline import run_pipeline
from app.schemas.competitor import PipelineRunResult

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/run", response_model=PipelineRunResult)
async def trigger_run() -> dict:
    """Run the pipeline now across all active competitors (synchronous)."""
    return await run_pipeline()
