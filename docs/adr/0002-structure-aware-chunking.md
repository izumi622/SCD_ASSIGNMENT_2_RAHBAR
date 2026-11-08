# ADR 0002: Structure-aware overlapping chunks

Status: Provisional until recall experiments are measured.

## Decision

Chunk by page and heading/paragraph boundaries and then split oversized blocks by word windows with configurable overlap. Each chunk retains page, source, section, version and superseded metadata. We keep headings and clause wording in evidence.

## Alternatives and trade-offs

Fixed-size nonoverlapping chunks are simpler, but can split definitions and clauses. Page boundaries protect citations but may split a multi-page section; this is a limitation. Overlap increases storage amplification. Run at least three configurations and record real recall@5 before claiming the choice is optimal.
