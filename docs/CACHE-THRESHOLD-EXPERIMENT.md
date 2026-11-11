# Cache Threshold Experiment

Isolated Redis cache-store/lookup probe using production SemanticCache, real Ollama vectors and a controlled cached response fixture; not end-to-end API requests.

| Threshold | False hits / pairs |
|---:|---:|
| 0.85 | 3 / 10 |
| 0.90 | 2 / 10 |
| 0.95 | 0 / 10 |

Lowest tested threshold with zero false hits: **0.95**.

## Detailed question pairs
- **P01** (summer versus regular course limits): cosine 0.937366; hit flags 0.85/0.90/0.95 = hit,hit,miss. Cached: Under current FAST-NUCES rules, what is the maximum number of courses in a summer semester? / Two courses.; Incoming: Under current FAST-NUCES rules, what is the maximum number of courses in a regular semester? / Five courses normally.
- **P02** (summer versus regular course limits, alternate phrasing): cosine 0.938103; hit flags 0.85/0.90/0.95 = hit,hit,miss. Cached: How many courses may a FAST-NUCES student register for during a summer semester? / Two courses.; Incoming: How many courses may a FAST-NUCES student register for during a regular semester? / Five courses normally.
- **P03** (required attendance versus condonable absence): cosine 0.801565; hit flags 0.85/0.90/0.95 = miss,miss,miss. Cached: Under FAST-NUCES rules, what percentage attendance is required in lectures and labs? / 100% attendance required.; Incoming: Under FAST-NUCES rules, what percentage absence may be condoned for genuine reasons? / Up to 20% absence may be condoned.
- **P04** (attendance versus exception, close phrasing): cosine 0.868165; hit flags 0.85/0.90/0.95 = hit,miss,miss. Cached: What is the FAST-NUCES attendance percentage requirement for a course? / 100% attendance required.; Incoming: What is the FAST-NUCES absence percentage that can be condoned for a course? / Up to 20% absence may be condoned.
- **P05** (semester freeze versus summer courses): cosine 0.785412; hit flags 0.85/0.90/0.95 = miss,miss,miss. Cached: Under FAST-NUCES rules, how many semesters may a student freeze? / Two semesters.; Incoming: Under FAST-NUCES rules, how many courses may a student take in summer? / Two courses, not semesters.
- **P06** (current withdrawal versus extra course rule): cosine 0.766864; hit flags 0.85/0.90/0.95 = miss,miss,miss. Cached: According to current June 2026 FAST-NUCES Rule 4.25, when is the course withdrawal deadline? / Last day of the makeup week.; Incoming: According to current June 2026 FAST-NUCES Rule 4.3, who may register for an extra regular-semester course? / Eligible final-year students.
- **P07** (minimum CGPA versus attendance minimum): cosine 0.726704; hit flags 0.85/0.90/0.95 = miss,miss,miss. Cached: What is the minimum CGPA required for bachelor graduation under FAST-NUCES rules? / 2.00 CGPA.; Incoming: What is the minimum attendance percentage required for lectures under FAST-NUCES rules? / 100% attendance.
- **P08** (academic warning versus withdrawal): cosine 0.738579; hit flags 0.85/0.90/0.95 = miss,miss,miss. Cached: Under June 2026 FAST-NUCES academic rules, what minimum CGPA avoids academic warning? / 2.00 CGPA.; Incoming: Under June 2026 FAST-NUCES academic rules, what is the deadline to withdraw from a course? / Last day of makeup week.
- **P09** (maximum summer courses versus maximum freeze semesters): cosine 0.785208; hit flags 0.85/0.90/0.95 = miss,miss,miss. Cached: What is the maximum number of courses allowed in summer at FAST-NUCES? / Two summer courses.; Incoming: What is the maximum number of semesters a student may freeze at FAST-NUCES? / Two semesters.
- **P10** (regular maximum versus final-year exception): cosine 0.828909; hit flags 0.85/0.90/0.95 = miss,miss,miss. Cached: Under current FAST-NUCES rules, what is the regular-semester course limit for most students? / Five courses normally.; Incoming: Under current FAST-NUCES rules, who is eligible for a sixth regular-semester course? / Final-year students.

## Limitations
Controlled fixtures with real SemanticCache, Redis and Ollama embeddings; not an end-to-end API accuracy test or a universal guarantee against false cache hits.
