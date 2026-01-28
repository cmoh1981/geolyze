"""Supabase REST client using httpx (no supabase-py dependency).

Uses the PostgREST API exposed at {SUPABASE_URL}/rest/v1/.
"""

from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from config import settings

_client: Optional[httpx.Client] = None


def _get_client() -> httpx.Client:
    """Lazy-initialise and return the httpx client for Supabase REST."""
    global _client
    if _client is None:
        _client = httpx.Client(
            base_url=f"{settings.SUPABASE_URL}/rest/v1",
            headers={
                "apikey": settings.SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            timeout=10.0,
        )
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
    }
    client = _get_client()
    resp = client.post("/jobs", json=row)
    resp.raise_for_status()
    data = resp.json()
    return data[0] if isinstance(data, list) and data else row


def update_job_status(
    job_id: str,
    status: str,
    completed_at: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    """Update the status columns of an existing job."""
    payload: dict[str, Any] = {"status": status}
    if completed_at:
        payload["completed_at"] = completed_at
    if error is not None:
        payload["error"] = error
    client = _get_client()
    resp = client.patch(f"/jobs?id=eq.{job_id}", json=payload)
    resp.raise_for_status()


def save_results(job_id: str, result_data: dict) -> None:
    """Persist full analysis results to the job row."""
    payload = {
        "result_data": result_data,
        "status": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    client = _get_client()
    resp = client.patch(f"/jobs?id=eq.{job_id}", json=payload)
    resp.raise_for_status()


def save_error(job_id: str, error_msg: str) -> None:
    """Record a failure on the job row."""
    payload = {
        "status": "failed",
        "error": error_msg,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    client = _get_client()
    resp = client.patch(f"/jobs?id=eq.{job_id}", json=payload)
    resp.raise_for_status()


def get_job(job_id: str) -> Optional[dict]:
    """Fetch a single job row by its ID."""
    client = _get_client()
    resp = client.get(f"/jobs?id=eq.{job_id}&select=*")
    resp.raise_for_status()
    data = resp.json()
    return data[0] if data else None


def get_user_monthly_job_count(user_id: str) -> int:
    """Count how many jobs a user has created in the current calendar month."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    client = _get_client()
    resp = client.get(
        "/jobs",
        params={
            "select": "id",
            "user_id": f"eq.{user_id}",
            "created_at": f"gte.{month_start.isoformat()}",
        },
        headers={**client.headers, "Prefer": "count=exact"},
    )
    resp.raise_for_status()
    # Count is in content-range header
    content_range = resp.headers.get("content-range", "")
    if "/" in content_range:
        total = content_range.split("/")[-1]
        return int(total) if total != "*" else 0
    return len(resp.json())


def get_user_tier(user_id: str) -> str:
    """Return the subscription tier for a user (defaults to 'free')."""
    client = _get_client()
    resp = client.get(f"/users?id=eq.{user_id}&select=plan")
    resp.raise_for_status()
    data = resp.json()
    if data and data[0].get("plan"):
        return data[0]["plan"]
    return "free"
