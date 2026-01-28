"""Thin wrapper around the Supabase admin client (service-role key).

All database helpers live here so route/worker code stays clean.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from supabase import Client, create_client

from config import settings

_client: Optional[Client] = None


def get_supabase() -> Client:
    """Lazy-initialise and return the Supabase admin client."""
    global _client
    if _client is None:
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    return _client


# ---------------------------------------------------------------------------
# Job CRUD
# ---------------------------------------------------------------------------


def create_job(job_id: str, geo_id: str, user_id: str) -> dict:
    """Insert a new analysis job row and return it."""
    row = {
        "id": job_id,
        "geo_id": geo_id,
        "user_id": user_id,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = get_supabase().table("jobs").insert(row).execute()
    return result.data[0] if result.data else row


def update_job_status(
    job_id: str,
    status: str,
    completed_at: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    """Update the status columns of an existing job.

    Only writes columns that actually exist on the jobs table:
    status, completed_at, error.
    """
    payload: dict[str, Any] = {
        "status": status,
    }
    if completed_at:
        payload["completed_at"] = completed_at
    if error is not None:
        payload["error"] = error
    get_supabase().table("jobs").update(payload).eq("id", job_id).execute()


def save_results(job_id: str, result_data: dict) -> None:
    """Persist full analysis results (plots, summary, metadata) to the job row."""
    get_supabase().table("jobs").update(
        {
            "result_data": result_data,
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", job_id).execute()


def save_error(job_id: str, error_msg: str) -> None:
    """Record a failure on the job row."""
    get_supabase().table("jobs").update(
        {
            "status": "failed",
            "error": error_msg,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", job_id).execute()


def get_job(job_id: str) -> Optional[dict]:
    """Fetch a single job row by its ID."""
    result = (
        get_supabase().table("jobs").select("*").eq("id", job_id).execute()
    )
    return result.data[0] if result.data else None


def get_user_monthly_job_count(user_id: str) -> int:
    """Count how many jobs a user has created in the current calendar month."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = (
        get_supabase()
        .table("jobs")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .gte("created_at", month_start.isoformat())
        .execute()
    )
    return result.count if result.count is not None else 0


def get_user_tier(user_id: str) -> str:
    """Return the subscription tier for a user (defaults to 'free')."""
    result = (
        get_supabase()
        .table("users")
        .select("plan")
        .eq("id", user_id)
        .execute()
    )
    if result.data and result.data[0].get("plan"):
        return result.data[0]["plan"]
    return "free"
