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

## D. Chunk-size ablation — observed 11 November 2026

The same nine-document FAST-NUCES corpus was indexed with three **word-based** chunk configurations into separate Chroma collections, leaving the deployed `rahbar` baseline intact. The two alternative indexer Jobs ran successfully in Kubernetes with the pinned `nomic-embed-text` embedding model (768 dimensions). A read-only Python evaluation compared all three collections against `eval/golden.yaml` and retrieved source/page evidence. Recall@5 is computed over the 13 answerable golden questions; the two must-abstain cases have no relevant target passages and are not included in retrieval recall.

| Size (words) | Overlap (words) | Collection | Indexed chunks | Stored chunk words | Recall@5 | Stored words / baseline |
| ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 200 | 25 | `rahbar_ablation_200_25` | 764 | 78,808 | 1.0000 | 1.040x |
| 400 | 50 | `rahbar` | 597 | 75,783 | 1.0000 | 1.000x |
| 600 | 75 | `rahbar_ablation_600_75` | 557 | 73,933 | 1.0000 | 0.976x |

The 200/25 Job completed in 129.4 seconds; 600/75 completed in 139.1 seconds. The 400/50 row is the existing production baseline, not a freshly timed Job. All three achieved identical top-five retrieval success on this golden set. Larger chunks decreased stored chunk-word volume by approximately 2.4% compared with baseline; smaller chunks increased it by approximately 4.0%.

**Measurement boundaries:** stored word counts are the sum of indexed passage words and are a proxy for stored text volume, not ChromaDB disk bytes. The last column is **relative to the 400/50 index**, not source-normalized overlap amplification. Strict source-normalized amplification (`sum(stored chunk words) / sum(extracted source words before overlap)`) remains unmeasured because a reliable unduplicated source-word denominator was not captured. The read-only test output printed Recall@5 and stored-word totals; per-question retrieval traces and Recall@3 were not captured in this experimental export. This evaluation measures retrieval, **not** end-to-end answer quality for each alternative index.

The student's preserved local evidence is `docs/CHUNKING-ABLATION-RESULTS.md` and `docs/chunking-ablation-results.json`. Indexer completion logs show `"indexer finished"` for both alternative Jobs. The first attempt at 200/25 failed when the Windows Ollama server was unavailable; the successful 200/25 Job was a fresh retry after the API pod confirmed an HTTP 200 and a 768-dimensional test embedding.

## E. Cache-threshold experiment — observed 11 November 2026

A controlled **component-level** experiment exercised RAHBAR's `SemanticCache` with the real Redis backend and `nomic-embed-text` embeddings from Ollama. Similar-looking questions with intentionally different expected answers were probed against three cosine-similarity thresholds. Production `CACHE_THRESHOLD` remained unchanged.

| Threshold | False semantic-cache hits on tested probes |
| ---: | ---: |
| 0.85 | 3 |
| 0.90 | 2 |
| **0.95** | **0** |

Thus, `0.95` was the **lowest tested threshold with zero observed false hits in this controlled probe set**. This justifies retaining the existing production default of `0.95` for the tested workload, but cannot prove the cache will never produce a false hit. The probe used controlled answer fixtures; it was not a full `/api/ask` generative accuracy test. The local outputs are `docs/cache-threshold-experiment.json` and `docs/CACHE-THRESHOLD-EXPERIMENT.md`. Treat their detailed cases as the primary evidence for exactly which questions were mistaken at lower thresholds.

## F. Remaining evidence and submission limitations

Four *deliberate* extraction/chunking/retrieval/source controlled failures, with before/after scores, are still pending in `docs/FAILURE-ANALYSIS.md`. Earlier real incidents (including indexer OOMKilled, wrong-version/rule answers and an unavailable Ollama server) are diagnostic evidence but should not be presented as completed controlled experiments. The full baseline 15-question API evaluation previously passed; the chunking comparison above instead evaluates top-five retrieval only.
