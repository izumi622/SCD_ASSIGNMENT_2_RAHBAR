# RAHBAR chunking ablation — verified results

**Date:** 11 November 2026

Three configurations were indexed from the same nine-document FAST-NUCES corpus using the `nomic-embed-text` embedding model. The read-only evaluation used the deployed RAHBAR retrieval implementation (`ChromaRetriever`) against the answerable questions in `eval/golden.yaml`. The two abstention questions have no gold relevant passage and are excluded from retrieval Recall@5.

| Chunk size / overlap (words) | Collection | Chunks | Indexed chunk words | Indexed words relative to 400/50 | Recall@5 (13 answerable questions) | Indexer duration |
|---|---|---:|---:|---:|---:|---:|
| 200/25 | `rahbar_ablation_200_25` | 764 | 78,808 | 1.040x | 1.0000 | 129.4 s |
| 400/50 | `rahbar` | 597 | 75,783 | 1.000x | 1.0000 | Not recorded in ablation |
| 600/75 | `rahbar_ablation_600_75` | 557 | 73,933 | 0.976x | 1.0000 | 139.1 s |

## Interpretation

All three indexed configurations achieved measured Recall@5 of 1.0000 on the 13 answerable golden questions. The 200/25 variant produced the most chunks and stored chunk words. The 600/75 variant produced the fewest chunks and stored chunk words. This experiment alone does not demonstrate equivalent answer quality, latency, or generalization beyond the 13-question golden set.

## Measurement limitations

- **Indexed chunk words** counts tokens separated by whitespace across the stored chunk documents; overlap is included.
- **Relative indexed words** is a baseline-relative ratio, not **source-normalized storage amplification**. The latter requires a cleaned prechunk corpus word-count denominator that was not captured.
- **Recall@3** was not preserved in the command output; it remains unreported rather than estimated.
- **Indexer duration** for 400/50 was not measured as part of these paired experiments; historical jobs are not treated as directly comparable.
- **Per-question evidence** was not saved due to an evaluator export hang; these aggregate measurements are transcribed from confirmed console outputs.
- Retrieval recall is not the same as factual answer accuracy or generation quality.

## Source evidence

- 200/25 Kubernetes Job `rahbar-ablation-200-25-r2`: `Complete 1/1`, indexer log `chunks=764`, `seconds=129.4`; Chroma count 764.
- 400/50 collection `rahbar`: Chroma count 597.
- 600/75 Kubernetes Job `rahbar-ablation-600-75`: `Complete 1/1`, indexer log `chunks=557`, `seconds=139.1`.
- Console evaluation printed `RESULT ... recall@5=1.0000` for all three collections, with stored word counts 78,808, 75,783, and 73,933 respectively.
