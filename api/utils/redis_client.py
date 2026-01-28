"""Upstash Redis REST client for job status caching."""

import json
import logging
from typing import Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)

JOB_TTL_SECONDS = 3600  # 1 hour

_client: Optional[httpx.Client] = None


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(
            base_url=settings.UPSTASH_REDIS_URL,
            headers={"Authorization": f"Bearer {settings.UPSTASH_REDIS_TOKEN}"},
            timeout=5.0,
        )
    return _client


def get_redis():
    """Return the httpx client (for API compatibility)."""
    return _get_client()


def update_status(
    r,
    job_id: str,
    status: str,
    progress: int,
    message: str,
) -> None:
    """Write job status to Upstash Redis with a 1-hour TTL."""
    try:
        client = _get_client()
        value = json.dumps({"status": status, "progress": progress, "message": message})
        client.post("/", json=["SET", f"job:{job_id}", value, "EX", str(JOB_TTL_SECONDS)])
    except Exception as e:
        logger.warning(f"Redis update_status failed: {e}")


def get_status(r, job_id: str) -> Optional[dict]:
    """Read job status from Upstash Redis."""
    try:
        client = _get_client()
        resp = client.post("/", json=["GET", f"job:{job_id}"])
        data = resp.json()
        result = data.get("result")
        if result is None:
            return None
        return json.loads(result)
    except Exception as e:
        logger.warning(f"Redis get_status failed: {e}")
        return None
