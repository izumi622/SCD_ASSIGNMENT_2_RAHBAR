# RAHBAR — Assignment 02 GitHub Handoff Context

> **Audience:** Assignment 03 partner / developer joining the project  
> **Prepared:** 22 November 2026  
> **Scope:** **The submitted Assignment 02 GitHub repository only**. This document describes what is committed to GitHub, what it does, where to find it, and what can be reused for Assignment 03. It does **not** assume that a working Kubernetes cluster, Docker images, corpus data or indexed database still exists on either student's laptop.

## 1. Source of truth and repository status

| Item | Detail |
|---|---|
| Project | **RAHBAR: grounded FAST-NUCES university-policy RAG assistant on Kubernetes** |
| Original repository | **[izumi622/SCD_ASSIGNMENT_2_RAHBAR](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR)** |
| Clone URL | `https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR.git` |
| Visibility | Public (verified from repository metadata) |
| Default branch | [`main`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/tree/main), marked protected by GitHub |
| Other visible branch | [`dev`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/tree/dev) |
| Assignment 02 submitted `main` commit | [`f9330fa517bf31908c3bfeb0611a9cce5fc2895e`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/commit/f9330fa517bf31908c3bfeb0611a9cce5fc2895e) |
| Previous delivery | [CI runs](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/actions/workflows/ci.yml) · [CD runs](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/actions/workflows/cd.yml) |

**Important:** All descriptions below concern the A02 repository and its submitted state. The A03 application, new RAGOps tests, traces, and release procedures **have not been implemented merely because A02 exists**. Treat A02 as a starting baseline, not as a completed A03 submission.

## 2. What we built (plain-language summary)

RAHBAR is a question-answering application that answers **from official FAST-NUCES documents**, and cites the relevant source and page. It is a **retrieval-augmented generation (RAG)** system: instead of asking a language model to recall university rules from general knowledge, the application retrieves relevant passages from indexed documents and supplies those passages to the model.

Two independent paths:

1. **Document/indexing path:** discover university PDFs/HTML → extract text (including OCR for scanned PDF pages) → clean and structure-aware chunking → embeddings from Ollama → store vectors, text, versions, and citation metadata in ChromaDB. Indexing runs as a **separate Kubernetes Job / scheduled CronJob**, not at API startup.
2. **Question/answer path:** browser UI → FastAPI question validation → eligible Redis cache lookup → embed question → retrieve and rerank Chroma passages → generate with Ollama/Qwen → validate evidence and citations → answer with citations **or abstain** when unsupported.

Main services in the codebase:

| Technology | Purpose | Where configured or implemented |
|---|---|---|
| FastAPI (Python) | `/api/ask`, validation, retrieval/generation orchestration, health, metrics | [`api/`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/tree/main/api) |
| Python indexer | PDF/HTML extraction, OCR, cleaning, chunking, embedding, indexing | [`indexer/pipeline/`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/tree/main/indexer/pipeline) |
| ChromaDB | Stores and searches vectorized document chunks and metadata | [`k8s/base/chroma.yaml`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/k8s/base/chroma.yaml) |
| Redis | Semantic answer cache; invalidated on index update | [`api/app/services/cache.py`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/api/app/services/cache.py) |
| Ollama | `nomic-embed-text` embeddings; `qwen2.5:7b` generation in the submitted real setup | [`k8s/base/configmap.yaml`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/k8s/base/configmap.yaml) |
| nginx + Ingress | Serves the browser chat page, routes `/api` requests | [`ui/`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/tree/main/ui) · [`ingress.yaml`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/k8s/base/ingress.yaml) |
| Kubernetes | API replicas, storage, indexing Jobs, health checks, scaling, security | [`k8s/`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/tree/main/k8s) |
| GitHub Actions | Automated code checks and SHA-tagged release workflow | [`.github/workflows/`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/tree/main/.github/workflows) |

### Key baseline settings from A02

- Default Chroma collection: **`rahbar`**.
- Standard chunk size / overlap: **400 / 50 whitespace-delimited words**.
- Embeddings: **`nomic-embed-text`, 768 dimensions** in the actual saved index.
- Generation: **`qwen2.5:7b`** through the Windows-host Ollama service in the earlier live demonstration. GitHub Actions use a **fixture embedding service + stub generator**, not the student's actual Ollama deployment.
- Retrieval normally returns **top 5** passages; current-policy search filters out documents marked `superseded` unless the query requests historical material.
- Semantic-cache similarity threshold: **0.95**.
- API input question length: **3–500 characters**.
- Baseline Kubernetes API Deployment: **3 replicas**, HPA capable of scaling; Chroma StatefulSet and Redis PVC for persistent data.

These settings are the starting values. For A03 change experiments, **do not silently change the baseline and then describe the new values as the A02 baseline**.

## 3. Repository tour — exactly where to look

All paths are **relative to the GitHub repository root**, not to a presumed local folder.

### Source code and public document provenance

| Path | What it contains | Why the partner needs it |
|---|---|---|
| [`README.md`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/README.md) | Architecture, installation order, API endpoints, tests and original instructions | First read; useful baseline, but some documentation is older than later experiments |
| [`api/app/schemas.py`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/api/app/schemas.py) | `AskRequest`, `Passage`, `Citation`, `Answer`, `AskResponse` | Defines the contract for UI, generator, and evaluations |
| [`api/app/services/answer.py`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/api/app/services/answer.py) | Cache eligibility, retrieval, generation, validation and fallback | Core answer pipeline and guardrails |
| [`api/app/retrieval/chroma.py`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/api/app/retrieval/chroma.py) | Vector retrieval, lexical reranking, version filtering | Baseline retrieval for A03 metrics and experiments |
| [`api/app/services/cache.py`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/api/app/services/cache.py) | Redis semantic cache | Baseline cache behavior and invalidation expectations |
| [`api/app/routes/metrics.py`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/api/app/routes/metrics.py) | Prometheus metrics | A03 observability extension point |
| [`indexer/pipeline/run.py`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/indexer/pipeline/run.py) | Document indexer orchestration | Insert A03 verification **before chunking** |
| [`indexer/pipeline/extract.py`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/indexer/pipeline/extract.py) | Poppler PDF text extraction, per-page Tesseract OCR, HTML handling | Implement/check new verification and quarantine rules |
| [`indexer/pipeline/clean.py`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/indexer/pipeline/clean.py) | Text cleanup | Check text quality / truncation behavior |
| [`indexer/pipeline/chunk.py`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/indexer/pipeline/chunk.py) | Structure-aware chunks, overlap, IDs | Candidate chunking experiments |
| [`indexer/pipeline/embed.py`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/indexer/pipeline/embed.py) | Ollama embeddings | Embedding-module measurements in A03 |
| [`indexer/pipeline/store.py`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/indexer/pipeline/store.py) | Chroma upserts, stale record handling, cache invalidation | **A03 incremental updates are not guaranteed:** add explicit unchanged/modified/deleted checks and evidence |
| [`corpus/sources.yaml`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/corpus/sources.yaml) | Public source document URLs and versions | Defines Batch A source list |
| [`corpus/fetch.py`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/corpus/fetch.py) | Downloads and verifies sources | Can rebuild original Batch A from public sources |
| [`corpus/MANIFEST.md`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/corpus/MANIFEST.md) | Nine document titles, URLs, sizes, SHA-256 hashes, versions | Provenance and consistency reference |
| [`ui/index.html`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/ui/index.html) | Existing minimal browser chat | Do not need to rewrite UI to extend the RAG backend |

### Kubernetes and release files

| File | Responsibility |
|---|---|
| [`k8s/base/kustomization.yaml`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/k8s/base/kustomization.yaml) | Base resource selection |
| [`k8s/base/configmap.yaml`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/k8s/base/configmap.yaml) | Runtime configuration values |
| [`k8s/base/api.yaml`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/k8s/base/api.yaml) | API Deployment and Service |
| [`k8s/base/chroma.yaml`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/k8s/base/chroma.yaml) | Stateful ChromaDB and PVC |
| [`k8s/base/redis.yaml`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/k8s/base/redis.yaml) | Redis and PVC |
| [`k8s/base/corpus.yaml`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/k8s/base/corpus.yaml) | Corpus volume and loader pod |
| [`k8s/base/indexer-job.yaml`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/k8s/base/indexer-job.yaml) | One-off indexing Job, deliberately separate from initial Kustomize apply |
| [`k8s/base/reindex-cronjob.yaml`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/k8s/base/reindex-cronjob.yaml) | Scheduled reindexing CronJob |
| [`k8s/base/hpa.yaml`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/k8s/base/hpa.yaml) | API horizontal scaling |
| [`k8s/base/networkpolicy.yaml`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/k8s/base/networkpolicy.yaml) | Default-deny and allowed network paths |
| [`k8s/base/ingress.yaml`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/k8s/base/ingress.yaml) | Routes browser/UI and API traffic |
| [`.github/workflows/ci.yml`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/.github/workflows/ci.yml) | GitHub CI jobs |
| [`.github/workflows/cd.yml`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/.github/workflows/cd.yml) | GitHub CD publishing and temporary deployment |

### Evaluation, explanations and existing evidence

| File or directory | What it gives the partner |
|---|---|
| [`eval/golden.yaml`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/eval/golden.yaml) | **15 A02 golden questions**, not the 25+ required for A03 |
| [`eval/run_eval.py`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/eval/run_eval.py) | Original recall/citation/abstention evaluator; extend for A03's new levels and metrics |
| [`eval/results.json`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/eval/results.json) | Previously committed measured result from the real-corpus deployment |
| [`eval/baseline.json`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/eval/baseline.json) | Saved comparison baseline |
| [`eval/version-comparison.md`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/eval/version-comparison.md) | Comparison of older and newer policy facts |
| [`docs/ARCHITECTURE.md`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/docs/ARCHITECTURE.md) | Responsibilities of each service and Kubernetes object |
| [`docs/PIPELINE.md`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/docs/PIPELINE.md) | Indexing/query design and measured baseline |
| [`docs/CORPUS.md`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/docs/CORPUS.md) | Nine sources and why they satisfy A02 corpus requirements |
| [`docs/CHUNKING-ABLATION-RESULTS.md`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/docs/CHUNKING-ABLATION-RESULTS.md) | Measured 200/25, 400/50, 600/75 retrieval comparison |
| [`docs/chunking-ablation-results.json`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/docs/chunking-ablation-results.json) | Machine-readable ablation results |
| [`docs/CACHE-THRESHOLD-EXPERIMENT.md`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/docs/CACHE-THRESHOLD-EXPERIMENT.md) | Measured false-cache-hit comparison |
| [`docs/cache-threshold-experiment.json`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/docs/cache-threshold-experiment.json) | Machine-readable cache probes |
| [`docs/FAILURE-ANALYSIS.md`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/docs/FAILURE-ANALYSIS.md) | Four controlled A02 subsystem experiments (with honest limitations) |
| [`docs/evidence/`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/tree/main/docs/evidence) | Captured A02 Kubernetes/endpoint evidence |
| [`docs/adr/`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/tree/main/docs/adr) | Architecture decision records |
| [`docs/AI-USAGE.md`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/docs/AI-USAGE.md) | AI assistance disclosure; review/update for A03 |

## 4. What the submitted GitHub results actually demonstrate

### Corpus and baseline

- **9 public FAST-NUCES resources**: seven PDFs and two HTML pages; archival review counted **279 PDF pages**. See [`docs/CORPUS.md`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/docs/CORPUS.md).
- Previous live Chroma collection indexed **597 chunks** with standard 400/50 word chunking.
- The saved A02 evaluation contains **15 golden questions**: 8 ordinary, 2 version-sensitive, 2 exact-term, 2 must-abstain, and 1 prompt-injection case.
- Saved scores: **Recall@3 = 1.0; Recall@5 = 1.0; citation metadata validity = 1.0; abstention correctness = 1.0; 0 response errors.** The reported strict answer checks passed **15/15**. Retrieval recall was measured on **13 questions with relevant target evidence**. Some of the full-API answers came from a warm Redis cache.
- **Limit:** metadata-valid citations are not independently proof that every claim in each answer is true; 15 questions are not broad coverage of all university questions.

### Chunking study (actual data, not an estimate)

| Word size / overlap | Collection | Chunks | Recall@5 on 13 answerable golden questions |
|---|---|---:|---:|
| 200 / 25 | `rahbar_ablation_200_25` | 764 | 1.0000 |
| **400 / 50 (shipped)** | `rahbar` | 597 | 1.0000 |
| 600 / 75 | `rahbar_ablation_600_75` | 557 | 1.0000 |

See the [`ablation report`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/docs/CHUNKING-ABLATION-RESULTS.md). These results measure retrieval at top five; they do **not** claim identical end-to-end generated-answer quality for all configurations.

### Cache threshold study

| Cosine threshold | False hits in the controlled probes |
|---|---:|
| 0.85 | 3 |
| 0.90 | 2 |
| **0.95 (shipped)** | **0** |

The study used real Redis/embeddings and controlled probe answers. It was **not** a complete LLM-generation benchmark. See [`cache report`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/docs/CACHE-THRESHOLD-EXPERIMENT.md).

### Controlled fault studies

1. **OCR disabled:** the scanned eight-page policy dropped from 1,780 extracted words / 21 chunks to **0 words / 0 chunks**.
2. **100-word chunks, zero overlap:** chunk count grew from 597 to **1,078**; the **four tested retrieval questions still succeeded**, so a regression was **not** shown for those queries.
3. **Top-k lowered from 5 to 1:** the designated PDF-page evidence for one summer-course question was no longer in the retrieved set.
4. **Older-version filter removed in an isolated process:** a superseded 2023 withdrawal rule ranked above the current 2026 rule.

These were **controlled subsystem diagnostics**, not four complete end-to-end 15-question candidate evaluations. See [`FAILURE-ANALYSIS.md`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/docs/FAILURE-ANALYSIS.md).

## 5. GitHub Actions and release history

**CI workflow:** [`.github/workflows/ci.yml`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/.github/workflows/ci.yml)

- Runs on pushes to `dev` and pull requests targeting `main`.
- Six jobs: **lint** (Ruff/Mypy), **test** (pytest/API coverage threshold 60%), **manifests** (Kustomize + strict kubeconform), **build** (API/UI/indexer images), **scan** (Trivy fixable HIGH/CRITICAL), **e2e-eval** (temporary kind cluster, fixture corpus/evaluation).
- Known successful submitted check: [**CI run #16**](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/actions/runs/43045043922).

**CD workflow:** [`.github/workflows/cd.yml`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/.github/workflows/cd.yml)

- Runs on pushes/merges to `main`.
- Three sequential jobs: **test → build-push → deploy** (`needs` controls the order).
- Publishes `rahbar-api`, `rahbar-indexer`, and `rahbar-ui` images to Docker Hub, **tagged with the full source commit SHA**, then tests deployment via temporary kind cluster and Ingress.
- Known successful submitted check: [**CD run #4**](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/actions/runs/43045948240), for `f9330fa...`.
- Docker Hub project image repositories from the A02 delivery: [API](https://hub.docker.com/r/irtaza3085/rahbar-api/tags), [indexer](https://hub.docker.com/r/irtaza3085/rahbar-indexer/tags), [UI](https://hub.docker.com/r/irtaza3085/rahbar-ui/tags).

**Critical distinction:** CI/CD's kind runs are **temporary fixture-based tests using stub generation**. They are **not a permanently hosted RAHBAR server** and they are **not a substitute for Assignment 03's live Kubernetes demonstration with the actual data**. The original A02 live demonstration was run separately by the student.

### Pull requests and branches

- [`main`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/tree/main) is the original protected submission branch. [`dev`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/tree/dev) was the integration branch.
- The A02 history contains **four merged pull requests**: [#1](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/pull/1), [#2](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/pull/2), [#3](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/pull/3), and [#4](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/pull/4).
- Final merged A02 snapshot is **`f9330fa...`**. Do not assume your new partner's Assignment 03 contributions are already recorded in the A02 history.
- GitHub `main` reports **protected**, but the exact branch-review rules should be checked in repository settings rather than assumed from the label alone.

## 6. Offline backup discovered — `A2.zip` (important update)

The project owner **also has an offline archive named `A2.zip`**, separately from GitHub. I inspected its ZIP directory and verified its archive integrity. It is not a running Kubernetes installation, but it materially reduces restoration work:

| Archive path (relative to the root of `A2.zip`) | What is present |
| --- | --- |
| `A2/rahbar-starter/` | Full local A02 project folder, including `api/`, `indexer/`, `ui/`, `k8s/`, `eval/`, `docs/`, and `scripts/` |
| `A2/rahbar-starter/corpus/raw/` | **All nine previously downloaded FAST-NUCES source files** (seven PDFs and two HTML files) plus `_index.json` |
| `A2/rahbar-starter/RAHBAR-final-submission.zip` | The previously created submission ZIP, nested within the backup |
| `A2/rahbar-starter/.git/` | A copied local Git directory and its history/refs; do **not** assume its checked-out branch exactly matches the submitted GitHub `main` |
| `A2/0) initial assignment/` through `A2/3.13)/` | Historical starter kits, phase patches, diagnostic scripts, and past handoff material |
| `A2/Assignment 02, RAHBAR Grounded RAG on Kubernetes.pdf` and `A2/Assignment2_Rubric.pdf` | The original assignment instructions and rubric |

**Practical effect for Assignment 03:** The nine original source files can be recovered directly from the ZIP, so you do **not** necessarily have to redownload the A02 corpus. Start new development from the submitted GitHub **`main`** (commit `f9330fa...`), then copy the original files into the new project's `corpus/raw/` **only after checking** the `_index.json` and source hashes. Keep the A02 source PDFs out of public Git, as before. The archive may also contain useful untracked experiment scripts that were not in the GitHub release.

**Security warning before sharing:** The ZIP contains a file named **`A2/dockerhub token.png`**, which may show a Docker Hub credential, and it includes `.git/` internals and other development leftovers. **Do not upload or forward the entire `A2.zip` to your partner or to a public repository without inspecting and removing sensitive material.** If the screenshot displays a real token, revoke/rotate that token. Share a sanitized copy of the needed source documents or working files instead.

The offline archive **does not contain** a live Minikube cluster, Docker image store, running API, or ready-to-use Chroma PVC. Those runtime pieces still need to be recreated for the A03 Kubernetes demo. The existing Docker Desktop installation and n8n data should remain untouched.

## 7. What is *not* stored in GitHub

The original project was cleaned up locally after the Assignment 02 demo. **A GitHub clone alone does not recreate a running pipeline.**

- **No active Minikube cluster, Kubernetes PVC data, Chroma vector DB state, Redis contents or running containers** are included in a Git repository.
- **No original nine downloaded PDF/HTML file bytes in GitHub `corpus/raw/`**: this directory is gitignored. GitHub contains the [`source list`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/corpus/sources.yaml), [`fetcher`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/corpus/fetch.py), and [`manifest with hashes`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/corpus/MANIFEST.md). A publisher could have updated a source file since the original download; report hash changes honestly.
- **No user Ollama model weights** in Git: the source configuration names the models but the actual weights belong to the runtime host.
- **No permanent production endpoint from GitHub Actions**: successful CI/CD checks do not leave an ongoing server running.
- **No guaranteed copies of untracked local experiment scripts or one-off Job logs on GitHub**: the measured reports and JSON files explicitly listed above are the committed record.
- **No GitHub Action secret values**: tokens such as `DOCKERHUB_TOKEN` are not stored in committed workflow files; a new repository owner must configure their own credentials if publishing images.

Do not overwrite or force-push the A02 `main` branch to adapt it for A03.

## 8. How the partner should use this for Assignment 03

**Recommended:** Keep Assignment 02 as a reference, and initialize a **separate Assignment 03 repository from this A02 source**. Both partners should commit their own meaningful A03 changes and use PRs. The new repository does not automatically inherit another repository's Actions secrets, branch protections, or Docker Hub publishing access.

A person starting with nothing local can obtain the tracked project source with:

```cmd
git clone --branch main https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR.git
```

This retrieves source and committed evidence **only**; it does not download source corpus binaries, install the model weights, install Kubernetes, or recreate persistent data. Consult [`README.md`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/README.md) and [`docs/ARCHITECTURE.md`](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/docs/ARCHITECTURE.md) before rebuilding runtime infrastructure.

**Assignment 03 builds new RAGOps capabilities on top of these files** (not implemented by merely cloning A02):

| A03 work | A02 starting point |
|---|---|
| **A — verify and update data** | `corpus/`, `indexer/pipeline/{run,extract,store}.py`, Kubernetes indexer Job; add quarantine, explicit document verification, incremental/rollback proofs |
| **B — offline testing at 3 levels** | `eval/golden.yaml`, `eval/run_eval.py`, `eval/baseline.json`; expand to 25+ questions and embedding/retrieval/answer statistics |
| **C — change & release gate** | A02 chunking experiment, `k8s/base/configmap.yaml`, baseline results; build comparative gate and pass/fail candidate process |
| **D — tracing and metrics** | FastAPI logging, request IDs, `api/app/routes/metrics.py`; implement full per-query JSONL trace, reconstruction and summaries |
| **E — drift & coverage** | A02 golden set + embedding retrieval; add live-query corpus, coverage calculations and golden-set updates |
| **F — Kubernetes rollout** | Existing `k8s/base/` and Jobs; add persistent quarantine/results/traces, evaluation Job, candidate Deployment/Service and rollback demonstration |
| **G — final report** | Existing `docs/`, `eval/` evidence; write the new A03 report and capture fresh terminal screenshots from your own A03 cluster |

If following the previously agreed ownership: **you own B, C, E, G; your partner owns A, D, F**. Both must understand and explain the entire system in the demo. The project requirement says both members must commit; your 33%-per-person minimum is your **team's target**, not text from the A03 PDF.

### Suggested branches for the *new* Assignment 03 repository

```text
main                          # tested submission
└── dev                       # integration
    ├── feat/part-a-data-management     # partner
    ├── feat/part-b-offline-testing     # you
    ├── feat/part-c-release-gate       # you
    ├── feat/part-d-observability      # partner
    ├── feat/part-e-drift-coverage     # you
    ├── feat/part-f-kubernetes         # partner
    └── docs/part-g-report             # you
```

**Integration dependencies to agree on early:** A's document IDs, quarantine paths and version metadata must be understood by B/E; B's evaluation JSON schema and C's release-gate result must be understood by F's evaluation Job / deployment; D's trace format must work with B's question IDs and F's trace PVC.

## 9. Fast partner reading order

1. [README](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/README.md) — what the system is and how the components interact.
2. [Architecture](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/docs/ARCHITECTURE.md) and [Pipeline](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/docs/PIPELINE.md) — which component owns which responsibility.
3. [Corpus manifest](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/corpus/MANIFEST.md) — which documents were used, which versions, and their hashes.
4. [Indexer](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/tree/main/indexer/pipeline) and [API](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/tree/main/api/app) — actual implementation, not merely descriptions.
5. [A02 golden questions](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/eval/golden.yaml), [results](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/eval/results.json), and [baseline](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/blob/main/eval/baseline.json).
6. [Kubernetes manifests](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/tree/main/k8s) and [CI/CD workflows](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/tree/main/.github/workflows).
7. [Completed experiment reports](https://github.com/izumi622/SCD_ASSIGNMENT_2_RAHBAR/tree/main/docs) — note measurement boundaries and older documentation that may still say “pending.”

---

**Bottom line:** The **GitHub repository is intact and reusable**, and a separate `A2.zip` archive preserves the original nine source documents and a local copy of the project. The running A02 installation and Kubernetes-indexed data were removed, but this does **not** mean the code or source documents must be recreated from scratch. Start A03 from the committed A02 source, implement the new RAGOps requirements, and collect fresh evidence from the new Kubernetes run.