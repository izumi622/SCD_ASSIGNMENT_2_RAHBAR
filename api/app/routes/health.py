"""Liveness is dependency-free; readiness requires a healthy, compatible index and Redis."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request, Response

from ..config import Settings

router = APIRouter()
log = logging.getLogger("rahbar.readiness")


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness: never talk to another service."""
    return {"status": "alive"}


def check_dependencies(settings: Settings) -> dict[str, str]:
    """Check the remote index plus Redis; return errors instead of leaking exceptions."""
    result: dict[str, str] = {}
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        collection = client.get_collection(settings.collection)
        count = collection.count()
        if count < 1:
            result["chroma"] = "empty collection"
        else:
            result["chroma"] = f"ok ({count} chunks)"
        metadata = collection.metadata or {}
        indexed_model = str(metadata.get("embed_model", ""))
        if indexed_model != settings.embed_model:
            result["embed_model"] = (
                f"mismatch: index={indexed_model or 'missing'} "
                f"api={settings.embed_model}"
            )
        else:
            result["embed_model"] = "ok"
    except Exception as exc:
        result["chroma"] = f"unavailable ({type(exc).__name__})"
        result["embed_model"] = "unverified"

    try:
        import redis

        conn = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
        )
        result["redis"] = "ok" if conn.ping() else "ping failed"
        conn.close()
    except Exception as exc:
        result["redis"] = f"unavailable ({type(exc).__name__})"
    return result


@router.get("/readyz")
def readyz(request: Request, response: Response) -> dict[str, Any]:
    checks = check_dependencies(request.app.state.settings)
    failures = {
        name: status for name, status in checks.items()
        if not (status == "ok" or status.startswith("ok ("))
    }
    if failures:
        response.status_code = 503
        log.warning("readiness dependency failed", extra={"failures": failures})
        return {"status": "not_ready", "checks": checks}
    return {"status": "ready", "checks": checks}
