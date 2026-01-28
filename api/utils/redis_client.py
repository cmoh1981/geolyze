import json
from typing import Optional

import redis as _redis

from config import settings

_pool: Optional[_redis.ConnectionPool] = None


def _get_pool() -> _redis.ConnectionPool:
    """Lazy-initialise a shared connection pool for Upstash Redis."""
    global _pool
    if _pool is None:
        _pool = _redis.ConnectionPool.from_url(
            settings.UPSTASH_REDIS_URL,
            decode_responses=True,
        )
    return _pool


def get_redis() -> _redis.Redis:
    """Return a Redis client backed by the shared pool."""
    return _redis.Redis(connection_pool=_get_pool())


# ---------------------------------------------------------------------------
# Convenience helpers for job status
# ---------------------------------------------------------------------------

JOB_TTL_SECONDS = 3600  # 1 hour


def update_status(
    r: _redis.Redis,
    job_id: str,
    status: str,
    progress: int,
    message: str,
) -> None:
    """Write job status to Redis with a 1-hour TTL."""
    r.setex(
        f"job:{job_id}",
        JOB_TTL_SECONDS,
        json.dumps(
            {
                "status": status,
                "progress": progress,
                "message": message,
            }
        ),
    )


def get_status(r: _redis.Redis, job_id: str) -> Optional[dict]:
    """Read job status from Redis, returning *None* if the key has expired."""
    raw = r.get(f"job:{job_id}")
    if raw is None:
        return None
    return json.loads(raw)
