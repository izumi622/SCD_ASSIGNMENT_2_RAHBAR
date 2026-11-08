"""Prometheus metrics at /metrics (section 4.8).

Request count and latency are wired up already. Add your own the same way:
retrieval latency, generation latency, cache hits, abstentions, fallbacks, tokens.
"""

from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

router = APIRouter()

REQUESTS = Counter("rahbar_requests_total", "HTTP requests", ["path", "status"])
LATENCY = Histogram(
    "rahbar_request_seconds",
    "HTTP request latency",
    ["path"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60),
)


RETRIEVAL_LATENCY = Histogram('rahbar_retrieval_seconds', 'Retrieval latency')
GENERATION_LATENCY = Histogram('rahbar_generation_seconds', 'Generation latency')
ABSTENTIONS = Counter('rahbar_abstentions_total','Responses abstaining from unsupported claims')
FALLBACKS = Counter('rahbar_fallbacks_total','Provider, schema or grounding fallbacks')

CACHE_LOOKUPS = Counter('rahbar_cache_lookups_total','Semantic cache lookups', ['result'])
CACHE_HIT_RATIO = Gauge('rahbar_cache_hit_ratio','Cache hit ratio per API process')
_cache_hits = 0
_cache_misses = 0

def track_cache_hit(hit: bool) -> None:
    global _cache_hits, _cache_misses
    if hit: _cache_hits += 1
    else: _cache_misses += 1
    CACHE_LOOKUPS.labels(result='hit' if hit else 'miss').inc()
    CACHE_HIT_RATIO.set(_cache_hits / (_cache_hits + _cache_misses))

@router.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
