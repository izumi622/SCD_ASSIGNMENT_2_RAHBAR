# Indexing, retrieval, chunking and cache — measured vs pending

## A. Index path (one-time and scheduled)

The real Job in `k8s/base/indexer-job.yaml` runs `python -m pipeline.run` with **no `--dummy` argument**, mounting `/corpus` from `corpus-data`. A weekly CronJob (`k8s/base/reindex-cronjob.yaml`) uses the same pipeline and source PVC. All indexing is outside the API process.

`indexer/pipeline/run.py` discovers source paths and version flags. `extract.py` invokes `pdfinfo` and `pdftotext -layout` for PDF pages, and falls back to bounded per-page Tesseract OCR for scanned pages. HTML uses a simple text/table parser. `clean.py` normalizes text; `chunk.py` keeps section/paragraph structure with configurable word overlap. `embed.py` sends batches to the pinned Ollama `/api/embed` model; `store.py` upserts Chroma vectors and metadata and invalidates the Redis cache revision after a successful index.

The current config is **`CHUNK_SIZE=400`, `CHUNK_OVERLAP=50`**, measured in whitespace-delimited words by `indexer/pipeline/chunk.py` (not GPT tokenizer tokens). The embedding model is `nomic-embed-text` with **768 dimensions** in the actual index. Chroma stores `source`, `section`, 1-based PDF `page`, `doc_version`, and `superseded` for every chunk. The student's live index count was **597**. Do not claim this count applies unchanged to other chunk configurations.

## B. Query path

The request contract lives in `api/app/schemas.py`; `api/app/routes/ask.py` invokes `api/app/services/answer.py`. The API checks Redis eligibility, embeds the question using the identical model, retrieves from Chroma and filters `superseded:false` for current-policy questions. `api/app/retrieval/chroma.py` blends semantic similarity and lexical term coverage to improve exact-rule search. `api/app/providers/llm/ollama.py` sends retrieved context to Qwen 2.5 with structured output expectations. The API validates citation metadata against actually retrieved passages and applies a conservative numerical sanity check and an extractive, source-page-constrained fallback when appropriate.

The Redis cache stores only grounded, cited answers for cacheable questions. Re-indexing invalidates existing cache entries. Because many questions in the final 15-question test were cache hits, the saved run measures the deployed **complete service**, not 15 independent uncached LLM generations.

## C. Retrieval and generation results observed on 8 November 2026

The student terminal showed `GATE PASSED` on the final 15-question `eval/golden.yaml` and strict audit **15/15**; observed `recall_at_3=1.0`, `recall_at_5=1.0`, `citation_validity=1.0`, `abstention_correctness=1.0`, `response_errors=0`. Results were saved to `eval/results.json` and `eval/baseline.json` locally. The tests include eight ordinary, two version-sensitive, two exact, two abstain and one prompt-injection case. The full answers should be reviewed for factual completeness; metadata validity alone is not factuality.

## D. Chunk-size ablation — **measurements not yet run**

The rubric requires three different chunk size/overlap settings tested on **the same nine-document corpus**. Do not treat the following as observed data; they are three experiment configurations to run using a separate Chroma collection or a full controlled re-index with rollback.

| Size (words) | Overlap (words) | Recall@5, final golden | Stored word amplification | Status |
| ---: | ---: | --- | --- | --- |
| 200 | 25 | **not measured** | **not measured** | To run |
| 400 | 50 | 1.0 in production evaluation | **not measured** | Only baseline recall measured |
| 600 | 75 | **not measured** | **not measured** | To run |

Amplification = total stored chunk word count / total extracted source word count (with overlap). Document the exact scripts, index revision and actual values after running experiments. A 1.0 result for 400/50 **must not** be copied to the other rows.

## E. Cache-threshold experiment — **measurements not yet run**

Current `CACHE_THRESHOLD=0.95` is a selected setting, but the requirement to compare thresholds and demonstrate a false hit is not yet experimentally satisfied. Evaluate at least 0.85, 0.90, and 0.95 on pairs of nearly identical but semantically different rules, with a fresh cache namespace between cases. Record the exact false hit, threshold, and final lowest-safe threshold. Cache hits and misses are available through `/metrics`.
