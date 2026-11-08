# RAHBAR deployed architecture

The source/manifest map in `README.md` is the logical architecture. Workload responsibilities are intentionally separated:

- **Indexer:** ephemeral `Job` or weekly `CronJob`, the only writer to Chroma. It reads the mounted document PVC, extracts/OCRs one document at a time, prepares section-aware chunks, batches embeddings through Ollama, and writes source metadata. Its completion is observable independently of the API's lifetime. Re-indexing does not trigger API rebuilds.
- **ChromaDB:** single-replica `StatefulSet` (`k8s/base/chroma.yaml`) with stable network identity and a `ReadWriteOnce` volume claim template (`chroma-data`, 2Gi). Chroma is not exposed outside the namespace through a NodePort or LoadBalancer. Single Chroma writer avoids concurrent collection migration in this coursework architecture.
- **Redis:** persistent `Deployment` + PVC and a ClusterIP Service. Only the API and indexer need Redis access. Store cacheable grounded answers only; invalidate after changed content is indexed.
- **FastAPI:** three replicas initially, HPA up to eight, managed with a rolling deployment. Each replica is stateless; it never extracts/indexes files. Readiness checks Chroma and its model pin, and liveness probes never depend on network services.
- **Ollama:** pinned embedding and generation models on the Windows host (outside Minikube). Production embedding and generation calls traverse `host.minikube.internal:11434`. The CI fixture harness instead runs a clearly labeled deterministic local embedding service and stub LLM; the mock is **not** an alternative real production embedding model.
- **nginx UI + Ingress:** a static nonroot web container; the Ingress maps `rahbar.local/` to the UI and `rahbar.local/api` to the API. The Chroma/Redis services are internal only.

`k8s/base/networkpolicy.yaml` declares default-deny and explicit DNS, API/indexer outbound and Chroma/Redis inbound rules. Calico is required to enforce the network policies on the student's Minikube; kind's default CNI used for CI may not enforce those same policies, so a successful CI smoke test is **not** independent evidence of network-isolation enforcement.

## First-installation dependency order

1. Namespace, ConfigMap, service accounts, storage, StatefulSet and service deployments.
2. Download source corpus, upload the files and `_index.json` to `corpus-data` via `corpus-loader`.
3. Apply **the real indexer Job** as a separate step. It is deliberately excluded from the base Kustomization until the corpus PVC is populated.
4. Wait for Job completion, then observe `/readyz`, ingress access, query/citation response, and HPA.

Never automatically start the dummy indexer or write to the collection from an API startup hook. This order is now documented and reproducible without rerunning the work on an existing populated Chroma PVC.
