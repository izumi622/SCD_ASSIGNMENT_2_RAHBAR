# Failure analysis — observed incidents vs controlled experiments

The assignment requests **four intentionally broken stages**, each with a before/after metric and diagnostic trace. The following incidents were genuinely observed during the student's local work, but **they are not substitutes for the four controlled experiments** until the team deliberately reproduces them and captures the evidence.

| Incident observed | Symptom | Stage | Observed diagnostic | Fix |
| --- | --- | --- | --- | --- |
| Memory pressure during real indexing | Some pods exited/failed under load | Extraction/indexing resources | `kubectl describe pod` reported `OOMKilled`, exit code **137** | Limited OCR to individual pages, raised indexer memory allowance and used `/tmp` emptyDir |
| q02 retrieved less authoritative student-handbook context | A fluent answer used the wrong policy context | Retrieval / source selection | Result's retrieved section/page did not point to the 2026 Rule 1.21 passage | Hybrid semantic/lexical retrieval and source version selection |
| q08 answered "sixteen" rather than **two** summer courses | Valid citation metadata but incorrect factual content | Generation and evidence selection | `expected_substring_present: false`, source page did not establish claim | Numeric evidence check and focused retry; current answer `2` cites PDF p.9 |
| q07 refused the two-semester freeze rule | `answered_from_context: false` even though recall@5=1.0 | Chunking and numeric grounding | Rule 4.18 split between “up to” and “2 semesters” on PDF p.22 | Same-page chunk reconstruction and grounded extractive fallback; live retest passed |

## Required controlled experiments — **not yet performed**

Run each one against an isolated index/namespace or restore the working configuration immediately afterwards. Do **not** destroy the real Chroma volume or change the final committed baseline to make a broken setup pass. For each, record exact command, start/end time, whether the API was ready, per-type recall@5, citation validity, abstention correctness and the log/metric used for diagnosis.

| Experiment (one change at a time) | Target symptom | Diagnostic signal | Status |
| --- | --- | --- | --- |
| A · Extraction: disable OCR on the eight-page scanned entrepreneurship policy | Missing scanned-only facts | OCR page counts, chunk count and missing source passages | **Not run** |
| B · Chunking: fixed 100-word chunks, zero overlap | Broken multi-sentence policy clauses | Recall@5 changes, increased split rule count | **Not run** |
| C · Retrieval: change `TOP_K` from 5 to 1 in an isolated setup | Relevant source may no longer be within the top returned passages | Recall@5, logs of `chunk_ids` and relevance scores | **Not run** |
| E · Source: remove `superseded:false` filter in an isolated setup | Historical 2023 rules may outrank 2026 | q09/q10 source version and citation page | **Not run** |

**How to diagnose without intentionally causing the fault:** inspect `kubectl logs` for the indexer/API, `/metrics` cache/latency and fallback counters, and `eval/results.json` per-question retrieved chunk IDs and citation metadata. For an actual experiment, preserve both the broken result and the restored passing result. Never call these predicted outcomes measured values until reproduced.
