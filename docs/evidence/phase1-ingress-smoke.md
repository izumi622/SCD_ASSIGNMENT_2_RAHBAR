# Phase 1 locally observed Ingress smoke test

Observed on 2026-11-08 from a Windows CMD session after fixing Chroma service links and the API startup stall. These are **starter stub** checks, not evidence for real RAG quality.

- `curl.exe --resolve rahbar.local:80:127.0.0.1 http://rahbar.local/` returned the complete chat UI HTML.
- `curl.exe --resolve rahbar.local:80:127.0.0.1 http://rahbar.local/healthz` returned `ok` from the **UI nginx** (the backend route lives behind `/api`).
- `POST http://rahbar.local/api/ask` question `What is the attendance policy?` returned JSON with `provider: "stub"`, three retrieved passages, and citation `stub-handbook.pdf / 1.1 About the stub`.
- `kubectl get hpa -n rahbar`: CPU 8%/70%, 3 minimum and 8 maximum replicas, 6 current replicas at the time.

Full screenshots and endpoint/IP records still need to be captured for the actual submission evidence.
