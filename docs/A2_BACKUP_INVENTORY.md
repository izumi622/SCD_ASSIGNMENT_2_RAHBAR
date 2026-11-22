# Assignment 02 backup audit — what is already on GitHub

Prepared 22 November 2026 from the uploaded `A2.zip` and the protected `main` branch at commit `f9330fa517bf31908c3bfeb0611a9cce5fc2895e`.

## Verified result

The submitted GitHub `main` already contains the full **tracked application code** and its required assignment evidence:
- `api/`: FastAPI, retrieval, model adapters, caching, guards and tests
- `indexer/`: extraction, OCR, cleaning, chunking, embeddings, Chroma writes and tests
- `ui/`: nginx static chat UI
- `k8s/`: Deployments, StatefulSet, Services, PVCs, Ingress, Jobs and CronJob
- `corpus/`: source list, manifest and downloader (but not downloaded third-party PDFs)
- `eval/`: golden questions, baseline, latest submitted evaluation results, tests and fixture materials
- `docs/`: architecture, pipeline, measured chunking/cache reports, failure analysis, ADRs and evidence
- `.github/workflows/`: CI and CD pipelines

**Comparison method:** The backup includes a local `.git/` containing the same `origin/main` commit SHA as GitHub. Comparing the backed-up working tree against that commit found no Python application/source file missing or changed. The six tracked files with differing byte hashes (`README.md`, `docs/PIPELINE.md`, `docs/FAILURE-ANALYSIS.md`, `docs/CACHE-THRESHOLD-EXPERIMENT.md`, `eval/results.json`, `eval/baseline.json`) were **identical after normalizing Windows CRLF to LF**. The backup includes a nested `RAHBAR-final-submission.zip` with the tracked submission snapshot.

## Useful backup-only items that are *not* in the submitted GitHub tree

The external backup `A2.zip` also contains:

| Backup path within `A2/rahbar-starter/` | Classification and handling |
| --- | --- |
| `corpus/raw/` (9 downloaded FAST-NUCES PDF/HTML files and `_index.json`) | **Keep outside public Git**. Restore locally from the ZIP for Assignment 03 Batch A or use `corpus/fetch.py`; verify against `corpus/MANIFEST.md` hashes |
| `rahbar_chunk_ablation_metrics.py` and `rahbar_cache_threshold_experiment.py` | Historical local experiment drivers. Their measured results **are committed** under `docs/`. These scripts depend on the old Minikube/Ollama setup; the cache probe's older Windows `kubectl cp` method had to be worked around |
| `rahbar-ablation-*.json`, `rahbar-failure-*.json`, `rahbar-real-index-*.yaml` | One-off Job manifests bound to the old cluster. Some contain old Kubernetes owner references and are **not portable** without regeneration |
| `eval/after-*.json`, `eval/q07-*.json`, `eval/retry3.json`, `eval/last3.json`, `eval/verified10.json`, `eval/smoke.json` | Intermediate diagnostics, not the final authoritative results. Use committed `eval/results.json` and `eval/baseline.json` for the A02 baseline |
| `eval/version-*-extract.txt` | Extracted portions of third-party documents; not required as public Git files |
| Phase patch ZIP files, debug instructions, `.pytest_cache/`, `__pycache__/`, `.git/` | Historical development artifacts, generated files, or duplicate Git internals, **not** appropriate for the tracked source tree |
| `RAHBAR-final-submission.zip` | Historical submission snapshot; redundant with the submitted `main` commit |
| Assignment PDF/rubric, Word/PDF guides and viva PDFs outside `rahbar-starter/` | Human-facing reference materials, not source code or runtime requirements |

## Security: never upload the whole backup

`A2.zip` includes `A2/dockerhub token.png`, which **may disclose a Docker Hub access token**. It has intentionally **not** been committed. If it shows a real token, revoke/rotate it through Docker Hub before sharing any archive. Never commit actual passwords, tokens, `.env` secrets, raw public-source PDFs or the nested `.git` folder.

## What is not recovered by a GitHub update

Neither the GitHub repository nor `A2.zip` is a running Minikube/Kubernetes cluster. The A02 cluster and its Chroma/Redis volumes were deliberately deleted after the demo; build/deploy/re-index them for A03. Do not confuse GitHub Actions' **ephemeral kind fixture deployment** with a permanently hosted production service. Docker Hub has published SHA-tagged project images at `irtaza3085/rahbar-api`, `irtaza3085/rahbar-indexer`, `irtaza3085/rahbar-ui`.

## Partner start here

1. [Full GitHub handoff](ASSIGNMENT_2_CONTEXT.md)
2. [Main README](../README.md) · [Architecture](ARCHITECTURE.md) · [Pipeline](PIPELINE.md)
3. [Manifest and source hashes](../corpus/MANIFEST.md)
4. [Final evaluation results](../eval/results.json) · [Golden set](../eval/golden.yaml)
5. [Chunking ablation](CHUNKING-ABLATION-RESULTS.md) · [Cache experiment](CACHE-THRESHOLD-EXPERIMENT.md) · [Controlled failure diagnostics](FAILURE-ANALYSIS.md)

Start A03 on a **new repository or branch**. Do not force-push or rewrite the protected submitted A02 `main`. The partner owns A/D/F; the other student owns B/C/E/G; both members need meaningful commits and full demo understanding.
