# RAHBAR — policy version evidence for q09 and q10

Reviewed: 2026-11-08. Ground truth was chosen from the exported source corpus **before** evaluating the new questions. Page values below are **PDF viewer page indices, 1-based**; printed handbook footers have different numbers.

| Golden ID | Rule | August 2023 (superseded) | June 2026 (current) | Expected answer and evidence for retrieval |
| --- | --- | --- | --- | --- |
| q09 | 4.25, course withdrawal | "Deadline to withdraw from a course is the last day of classes." `undergraduate-academic-rules-aug-2023.pdf`, PDF p.16. | "The deadline to withdraw from a course is the last day of the makeup week of every semester." `academic-rules-handbook-jun-2026.pdf`, PDF p.23. | Current deadline is **last day of makeup week**; expected evidence: current PDF p.23. |
| q10 | 4.3, extra regular-semester courses | Normal load is 5 courses, but students may register for more **if not getting ahead of their batch**. `undergraduate-academic-rules-aug-2023.pdf`, PDF p.14. | Normal load is 5 courses. **A final-year student** may register for **one additional course, inclusive of FYP**. `academic-rules-handbook-jun-2026.pdf`, PDF p.19. | Answer: **final-year student**, one extra course inclusive of FYP; expected evidence: current PDF p.19. |

The system's current-version retriever should rely on the 2026 text and exclude superseded 2023 content when answering questions asking for the current rule.

## q14 — must abstain

Question: "What is the exact lunch menu at the FAST-NUCES Islamabad campus cafeteria for December 1, 2027?"

This is future-specific information not supported by the historical academic rules, handbooks, prospectus, annual reports and website snapshots assembled by 2026-11-08. The earlier draft question about hostel-room reservations has been replaced: we have not reviewed all nine full documents for hostel procedures. The correct behavior for q14 is **answered_from_context=false**, **no citations**, and a statement that the corpus does not cover the request. This remains a live test, not an assumed pass.

## Evaluation limitations

- `recall@3` / `recall@5` are evidence-retrieval measures, not answer-accuracy percentages.
- Citation validity checks the cited metadata against retrieved chunks; it does not prove the cited page supports each claim.
- `expected_substring_present` is a lightweight answer sanity check, not a full semantic judge.
- q09/q10 responses require manual review to confirm current-version wording, not merely a keyword hit.
- Do not edit the ground-truth expectations in response to model output. Report failures faithfully.
