# Corpus design and provenance

RAHBAR indexes **nine publicly available FAST-NUCES resources**: **seven PDFs and two HTML pages**. The saved manifest contains each URL, version label, bytes, download date and SHA256. The offline audit of the student's current archive counted **279 total PDF pages**. The observed live Chroma collection held **597 chunks** after successful indexing. The document bytes in `corpus/raw/` are excluded from Git; the loader fetches them again and checks the manifest.

| Document/source | What it covers | Evidence used in tests |
| --- | --- | --- |
| Undergraduate Academic Rules (Aug 2023) | Historical rulebook, marked `superseded=true` | Comparison with current registration and withdrawal policies |
| Academic Rules Handbook (Jun 2026) | Current policy, attendance, CGPA, registration, summer courses, academic honesty | Rule 1.21 on PDF p.10; Rule 4.3 on PDF p.19; Rule 4.18 on PDF p.22; Rule 4.25 on PDF p.23 |
| Prospectus 2026, Academic Rules and Regulations | Separate published summary and cross-reference | Summer semester and degree-regulation passages |
| Student Handbook (Jun 2026) | Student information and conduct | Useful for comparison and cross-document grounding |
| Annual Report 2019–20 | University report | Historical organizational information |
| Annual Report 2023–24 | University report | More recent organizational information |
| Fee Structure HTML page | Tabular university fee information | Table/row extraction path |
| Grading HTML page | Grades and evaluation context | Exact grade terms |
| Faculty Entrepreneurship and Technical Start-ups Policy (May 2022) | Detailed definitions and research policy | OCR stress case |

## Seven required corpus properties

1. **At least six genuine source documents:** the manifest has nine verified source entries.
2. **At least forty pages:** the seven PDFs total 279 pages in the archived-source audit.
3. **Two editions of one policy:** the August 2023 undergraduate rules and June 2026 rules are retained with explicit `doc_version` and `superseded` metadata.
4. **A scanned/poorly-extractable document:** the faculty entrepreneurship policy is an eight-page PDF with no detected embedded font rows. OCR is handled page-by-page using Poppler and Tesseract in `indexer/pipeline/extract.py`. Confirm OCR evidence with logs and a screenshot of one page.
5. **A long definition/section vulnerable to fixed-size splitting:** registration and academic-assessment rules span long textual blocks; Rule 4.18 was actually split at “up to / 2 semesters” and required a source/page-constrained reconstruction.
6. **Tables:** the 2026 fee and grading HTML sources contain table cells; the extractor retains separators and the cleaner normalizes whitespace. Document one raw row and its resulting chunk for submission evidence.
7. **A deliberately absent topic:** there is no supported campus policy about parking spaceships on Mars; the future December 2027 cafeteria lunch menu is likewise not present. Both are `must_abstain` golden tests.

## Reproducibility

`corpus/sources.yaml` declares which documents to download. `corpus/fetch.py` writes `corpus/raw/` and `_index.json` so the indexer can preserve version metadata. `corpus/MANIFEST.md` records file hashes and URLs. **If a publisher changes or removes a PDF, the original hash is not reproducible by a fresh download**; preserve the acquisition logs and report any resulting mismatch rather than silently claiming the bytes are unchanged.

Version filtering is implemented by `api/app/retrieval/chroma.py`. Normal questions filter `superseded:false`; explicit historical queries may include older documents. An old answer is not “wrong” if the question explicitly asks about the old edition, but it must be clearly dated.

**Evidence still to attach:** OCR trace/scan screenshot; before/after HTML table row; the precise 279-page counting command, if the submitting team wants independently reproducible page-count proof.
