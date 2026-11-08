# ADR 0003: Redis semantic cache

Status: Implemented as a small bounded-workload baseline; threshold not yet experimentally tuned.

## Decision

Use persistent Redis because it already provides a bounded TTL, atomic writes, a durable key store and easy cache invalidation on re-index. Queries are embedded with the pinned model. Search candidates by cosine similarity and return a hit only above the ConfigMap threshold. Abstentions, unsupported citations, historical comparisons and likely follow-up questions are excluded. The index revision and bulk deletion invalidate old entries after reindex.

## Trade-offs

The current scan-based similarity lookup is O(N), so it is suitable for this class demo and a small number of entries, not production scale. A dedicated vector cache (e.g. Chroma collection) would accelerate nearest-neighbour lookups. The default `CACHE_THRESHOLD=0.95` is a provisional safety-biased setting; evaluate multiple thresholds and false hits before submission.
