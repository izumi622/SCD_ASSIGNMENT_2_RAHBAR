# ADR 0001 — Indexing runs as a Kubernetes Job

- **Status:** Accepted for Phase 1 bootstrap; revisit atomic reindex design for the real pipeline.
- **Context:** The API runs three replicas. Chroma owns one persistent index. Indexing on
  every API startup would cause concurrent writes, repeated work on restart and failed readiness.
- **Decision:** `k8s/base/indexer-job.yaml` is the sole writer to the Chroma collection.
  The weekly `k8s/base/reindex-cronjob.yaml` uses the same indexer image. The API only
  reads; its readiness depends on a non-empty collection and matching embedding model.
- **Consequences:** The initial API replicas may run but not become Ready before the Job
  succeeds. A pod restart never rebuilds the index. Reindexing need not restart the API.
- **Limitations / follow-up:** The Phase 1 Job writes only a dummy index and currently
  replaces the collection directly. Before real traffic, implement staged/atomic index
  replacement and cache invalidation. Demonstrate the decision with actual cluster evidence.
