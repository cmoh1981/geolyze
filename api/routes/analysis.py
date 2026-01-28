"""Analysis routes: submit jobs, poll status, fetch results."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from auth import get_current_user
from models import (
    AnalyzeRequest,
    AnalyzeResponse,
    JobResultsResponse,
    JobStatus,
    JobStatusResponse,
)
from utils.redis_client import get_redis, get_status
from utils.supabase_client import (
    create_job,
    get_job,
    get_user_monthly_job_count,
    get_user_tier,
)
from workers.analysis_worker import run_analysis

router = APIRouter()

# Rate-limit thresholds per tier
_TIER_LIMITS: dict[str, int | None] = {
    "free": 3,       # 3 analyses per calendar month
    "pro": None,     # unlimited
    "admin": None,
}


# ------------------------------------------------------------------
# POST /api/analyze
# ------------------------------------------------------------------


@router.post("/analyze", response_model=AnalyzeResponse)
async def start_analysis(
    body: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
) -> AnalyzeResponse:
    """Submit a new GEO analysis job.

    * Validates the GEO ID format (enforced by the Pydantic model).
    * Checks the user's monthly quota.
    * Creates a job record in Supabase and seeds status in Redis.
    * Kicks off the background pipeline.
    """
    user_id: str = user["user_id"]
    geo_id: str = body.geo_id.strip().upper()

    # --- quota check ---
    tier = get_user_tier(user_id)
    limit = _TIER_LIMITS.get(tier, 3)
    if limit is not None:
        used = get_user_monthly_job_count(user_id)
        if used >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Monthly analysis limit reached ({limit}/{limit}). "
                    "Upgrade to Pro for unlimited analyses."
                ),
            )

    # --- create job ---
    job_id = str(uuid.uuid4())
    create_job(job_id, geo_id, user_id)

    # Seed Redis so the very first /status poll returns something
    try:
        r = get_redis()
        from utils.redis_client import update_status

        update_status(r, job_id, "pending", 0, "Job queued")
    except Exception:
        pass  # non-fatal

    # --- launch background worker ---
    background_tasks.add_task(run_analysis, job_id, geo_id, user_id)

    return AnalyzeResponse(
        job_id=job_id,
        status=JobStatus.pending,
        message="Analysis job created. Poll /api/status/{job_id} for progress.",
    )


# ------------------------------------------------------------------
# GET /api/status/{job_id}
# ------------------------------------------------------------------


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    user: dict = Depends(get_current_user),
) -> JobStatusResponse:
    """Return the current status of an analysis job.

    Reads from Redis for speed; falls back to Supabase if Redis misses.
    """
    # Try Redis first
    try:
        r = get_redis()
        cached = get_status(r, job_id)
    except Exception:
        cached = None

    # Fallback: fetch from Supabase (also verifies the job exists)
    job = get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Ownership check
    if job.get("user_id") != user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this job",
        )

    # Prefer Redis values (more up-to-date during a run)
    if cached:
        s = cached["status"]
        p = cached["progress"]
        m = cached["message"]
    else:
        s = job.get("status", "pending")
        p = job.get("progress", 0)
        m = job.get("message", "")

    return JobStatusResponse(
        job_id=job_id,
        geo_id=job.get("geo_id", ""),
        status=JobStatus(s),
        progress=p,
        message=m,
        created_at=job.get("created_at", ""),
        completed_at=job.get("completed_at"),
    )


# ------------------------------------------------------------------
# GET /api/results/{job_id}
# ------------------------------------------------------------------


@router.get("/results/{job_id}", response_model=JobResultsResponse)
async def get_job_results(
    job_id: str,
    user: dict = Depends(get_current_user),
) -> JobResultsResponse:
    """Fetch the full analysis results for a completed job."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job.get("user_id") != user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this job",
        )

    if job.get("status") != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is not completed yet (status: {job.get('status')})",
        )

    result_data: dict = job.get("result_data") or {}
    if not result_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result data not available",
        )

    return JobResultsResponse(
        job_id=job_id,
        geo_id=job.get("geo_id", ""),
        metadata=result_data.get("metadata", {}),
        data_type=result_data.get("data_type", "unknown"),
        plots=result_data.get("plots", {}),
        summary=result_data.get("summary", {}),
        de_results=result_data.get("de_results"),
    )
