# Failure analysis — observed incidents vs controlled experiments

The assignment requests **four intentionally broken stages**, each with a before/after metric and diagnostic trace. The following incidents were genuinely observed during the student's local work, but **they are not substitutes for the four controlled experiments** until the team deliberately reproduces them and captures the evidence.

| Incident observed | Symptom | Stage | Observed diagnostic | Fix |
| --- | --- | --- | --- | --- |
| Memory pressure during real indexing | Some pods exited/failed under load | Extraction/indexing resources | `kubectl describe pod` reported `OOMKilled`, exit code **137** | Limited OCR to individual pages, raised indexer memory allowance and used `/tmp` emptyDir |
| q02 retrieved less authoritative student-handbook context | A fluent answer used the wrong policy context | Retrieval / source selection | Result's retrieved section/page did not point to the 2026 Rule 1.21 passage | Hybrid semantic/lexical retrieval and source version selection |
| q08 answered "sixteen" rather than **two** summer courses | Valid citation metadata but incorrect factual content | Generation and evidence selection | `expected_substring_present: false`, source page did not establish claim | Numeric evidence check and focused retry; current answer `2` cites PDF p.9 |
| q07 refused the two-semester freeze rule | `answered_from_context: false` even though recall@5=1.0 | Chunking and numeric grounding | Rule 4.18 split between “up to” and “2 semesters” on PDF p.22 | Same-page chunk reconstruction and grounded extractive fallback; live retest passed |

## Controlled configuration experiments — observed 11 November 2026

Four deliberately altered configurations were tested **against the student's live Minikube cluster** using one-off Kubernetes Jobs or a separate Python process. The production `rahbar` collection was **not** overwritten. These were *subsystem experiments*, not full 15-question end-to-end API evaluations of all four broken variants. Reported facts below come from the student's terminal outputs; do not extrapolate unmeasured generation metrics.

| Stage | Controlled change | Working state | Altered state | What was actually demonstrated |
| --- | --- | --- | --- | --- |
| **A — extraction** | Disable fallback OCR for the eight-page scanned entrepreneurship policy | 8/8 pages with text; **1,780 words; 21 chunks** at 400/50 | 0/8 pages with text; **0 words; 0 chunks** | **Confirmed extraction failure**: all searchable text from this scanned PDF is lost |
| **B — chunking** | Index the same nine documents at **100 words / 0 overlap** rather than 400/50 | **597 chunks** in `rahbar`; expected source/page evidence in q07–q10 top five **4/4** | **1,078 chunks** in isolated `rahbar_failure_100_0`; expected source/page evidence in q07–q10 top five **4/4** | **Negative result** on the four tested questions: no demonstrated evidence loss. More fragments alone do **not** prove a failure |
| **C — retrieval** | Request **TOP_K=1** instead of 5 for the summer-course q08 question | `TOP_K=5`: designated June 2026 academic-rules **PDF page 9** is rank **2**, so gold evidence present | `TOP_K=1`: only June 2026 **PDF page 28** is returned, so designated page 9 is absent | **Confirmed golden-evidence loss** for q08 (specific page-target hit: **1 → 0**). Does not itself prove a wrong final answer; page 28 may also contain relevant content |
| **E — source/version selection** | In a diagnostic Python process, allow superseded documents in the candidate pool by disabling the default version filter | Current-rule withdrawal question: **June 2026 policy, PDF page 23 ranked first**; 0 older-2023 documents in top five | **August 2023 policy, PDF page 16 ranked first**; 1 older-2023 document in top five | **Confirmed source contamination/top-rank regression**. Wrong generated answer not independently measured |

### A. OCR-off extraction — diagnostic and restoration

- Isolation: a **one-off** Kubernetes Job named `rahbar-failure-ocr-off` mounted the existing read-only-in-practice corpus path and ran a diagnostic extract/chunk script. It did **not** invoke the indexer's Chroma store and did not reconfigure the deployed API.
- Source: `faculty-entrepreneurship-and-technical-start-ups-policy.pdf` (8 scanned pages).
- Before: `extract(...)` with the normal Poppler → Tesseract per-page OCR fallback, followed by the production cleaner and `chunk(doc, 400, 50)`.
- Fault injection: temporarily replace `pipeline.extract._ocr_pdf_page` with a function returning an empty string **inside the isolated Python process**, then rerun extraction/cleaning/chunking on the same PDF.
- Live Job observation: `kubectl get job rahbar-failure-ocr-off -n rahbar` → **Complete 1/1**, duration **19 seconds**.
- Diagnostic output, fields `(pages, nonempty_pages, words, chunks_400_50)`:

```text
NORMAL: (8, 8, 1780, 21)
NO_OCR: (8, 0, 0, 0)
```

- Diagnosis: Poppler's text layer did not yield usable text for the scanned pages, so removing the OCR fallback eliminated **all** indexed passage content from this particular PDF. Keeping per-page Tesseract OCR is the restored and deployed behavior. The measured `21` is for this **one document**, not the whole corpus.

### B. Zero-overlap, 100-word index — diagnostic and restoration

- Isolation: Kubernetes Job `rahbar-failure-chunk-100-0`, using `CHUNK_SIZE=100`, `CHUNK_OVERLAP=0`, `CHROMA_COLLECTION=rahbar_failure_100_0`. Corpus and embedding model are unchanged. The original production `rahbar` collection remains at 400/50.
- Live Job observation: **Complete 1/1**, `indexer finished` with **1,078 chunks** in **151.9 seconds**. Baseline has **597 chunks**.
- Measured comparison: invoking the actual `ChromaRetriever.retrieve(question, k=5)` against both collections for q07 (June 2026 page 22), q08 (page 9), q09 (page 23), and q10 (page 19), matching exact source **and PDF page**. All **four** questions returned the designated evidence within the top five in **both** collections.
- Diagnosis: this variant produces **481 additional fragments** (**80.6%** more indexed chunks), but the four tested questions did **not** expose a retrieval regression. It is **not** honest to label this variant a failed recall run. Zero overlap could harm cross-boundary evidence in other questions, but that is a hypothesis, not an observed outcome. Restoration means retaining the original production 400/50 collection, which was never overwritten.

### C. Restrict retrieval from TOP_K=5 to 1 — diagnostic and restoration

- Isolation: direct `ChromaRetriever` calls in a temporary `kubectl exec` Python subprocess in the running API image; no Deployment or ConfigMap was edited.
- Tested exact golden question **q08**: `What is the maximum number of courses an undergraduate may register for in a summer semester?` Expected `eval/golden.yaml` evidence: `academic-rules-handbook-jun-2026.pdf`, **PDF page 9**.
- Observed before/after:

```text
TOP_K=1: [('academic-rules-handbook-jun-2026.pdf', 28)]
TOP_K=5: [('academic-rules-handbook-jun-2026.pdf', 28),
          ('academic-rules-handbook-jun-2026.pdf', 9),
          ('academic-rules-handbook-jun-2026.pdf', 29),
          ('prospectus-2026-academic-rules-and-regulations.pdf', 3),
          ('academic-rules-handbook-jun-2026.pdf', 19)]
```

- Diagnosis: top-one evidence dropped the **gold-target page 9** that appears at rank 2 with top-five retrieval; the designated-page hit changed **1 → 0**. Additional q07, q09, and q10 smoke probes still matched top one, showing the failure is **query-specific**. The production setting remains `TOP_K=5`. We did not run generation/citation checking for the broken variant, and page 28's factual content was not ruled out.

### E. Disable source-version protection — diagnostic and restoration

- Isolation: direct API retriever in a subprocess, with a temporary local monkeypatch `app.retrieval.chroma._OLD_VERSION = re.compile('.*')` after a normal retrieval call. This changes only the test process so the retriever passes `where=None` rather than `where={'superseded': False}` for the second call. No persistent code, ConfigMap, Chroma metadata, or API replica was changed.
- Diagnostic question: `Under the current June 2026 academic rules, is the last day of classes the withdrawal deadline under Rule 4.25?`
- Observed normal top-five **source/page** entries: 2026 academic rules p23, 2026 academic rules p29, 2026 prospectus p2, 2026 student handbook p29, 2026 academic rules p17; **zero** 2023 source entries.
- Observed broken top-five: **2023 academic rules p16 ranked #1**, then 2026 academic rules p23, 2026 academic rules p29, 2026 prospectus p2, 2026 student handbook p29; **one** 2023 source entry.
- Diagnosis: superseded 2023 Rule 4.25 says the deadline is the *last day of classes*; current 2026 Rule 4.25 says *last day of makeup week*. The broken candidate pool ranked the obsolete rule above the current one, creating a risk of confidently answering with old policy. **Actual generation of a wrong answer was not tested.** Normal filtering remains intact outside this subprocess.

### Evidence scope and further work

The baseline 15-question API evaluation in `eval/results.json` previously passed **Recall@3=1.0**, **Recall@5=1.0**, **citation validity=1.0**, **abstention correctness=1.0**, with zero response errors. That baseline is **not** a before/after full evaluation for each broken variant. The four experiments above instead measure: document extraction volume, four-question retrieval evidence coverage, a single-question top-k evidence change, and top-ranked source version. Do not report per-type Recall@5, citation validity, abstention rate, or generated-answer correctness for a broken configuration because those were **not measured**.

Reproduction artifacts are present in the student's local working tree as `rahbar-failure-chunk-100-0.json` and `rahbar-failure-ocr-off.json` (untracked at the time of test); one-off job/pod logs are accessible through `kubectl logs -n rahbar job/<job-name> -c indexer` until cluster cleanup. The base production design, measured chunk-size ablation, and cache-threshold results are documented in `docs/PIPELINE.md`, `docs/CHUNKING-ABLATION-RESULTS.md`, and `docs/CACHE-THRESHOLD-EXPERIMENT.md`.
