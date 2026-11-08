# AI assistance disclosure — RAHBAR

**Tool:** ChatGPT (OpenAI GPT-6), used extensively during RAHBAR implementation and troubleshooting, especially 8 November 2026. This is a collaborative, AI-assisted project, **not** an unaided manual implementation.

## Tasks for which ChatGPT generated or materially revised code

- Kubernetes manifests and corrections: Chroma StatefulSet and PVC, service accounts and NetworkPolicy, API deployment, probes, HPA, Redis, loader PVC and weekly re-index Job.
- Real corpus acquisition/indexer integration, OCR and memory-bounded extraction, structure-aware chunking, embedding and Chroma upserts, cache invalidation, API generation and metadata citation checks, version filtering.
- Production diagnostics and fixes: cluster resource pressure, API startup readiness, embedding/model compatibility, Ollama timeouts, hybrid lexical reranking, numerical evidence validation, source-page chunk reconstruction and an extractive fallback for a missed semester-freeze question.
- Evaluation code, golden-set assembly and version verification, numeric-answer equivalence, stricter answer-content gate, and experiment reporting scaffolding.
- GitHub Actions workflow **drafts** and fixture-only offline embedding harness (these are not verified remote successes until the team runs them).
- Engineering documentation drafts and commands.

## Verification actually performed by the student

Windows CMD logs provided to the assistant showed successful Docker builds, image loads, rolling updates, healthy readiness with **597 real chunks**, and the live q07 result citing the 2026 handbook page 22. The final live evaluation command reported `GATE PASSED` followed by a stricter offline audit of **15/15** with no response errors on 8 November 2026. These outputs are evidence of the user's **local** cluster; they are **not** evidence of a successful GitHub Actions run or Docker Hub publication. Some final evaluation results came from Redis cache; the earlier individual fresh q07 request also succeeded.

## What the team must do independently

Review and understand the generated files, run/check any workflow changes, amend the AI disclosure if other tools contributed, and provide genuine measured results and screenshots for uncompleted requirements. GitHub Actions run URLs, branch protection, SHA-tagged images, three chunk configurations, cache-threshold experiments and four *deliberately broken* failure stages must not be claimed finished without actually doing them.

**Reason for changes after verification:** q02 initially used less authoritative context, q08 initially returned a wrong number, and q07 initially refused an answer because a quantitative rule was split across chunks. They were repaired with better retrieval, numerical safeguards and citation-preserving extraction. The student ran live tests after receiving the patches and returned the results.
