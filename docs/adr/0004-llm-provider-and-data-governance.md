# ADR 0004: LLM provider and public-document governance

Status: Preliminary — live service must still be verified.

## Decision

Use `ollama-host` with `llama3.2:3b` for generation and `nomic-embed-text` for both indexing and querying. The embedding model and generation temperature live in one Kubernetes ConfigMap. The Ollama provider is swappable through the provider interface; hosted credentials, if used, must come from a Kubernetes Secret, never Git.

Only the public FAST-NUCES website documents listed in `corpus/MANIFEST.md` may be indexed. Commit their URLs, checksums, downloader and provenance rather than university PDFs. Treat retrieved text as untrusted input and validate generated citations against retrieved passages. The application must abstain rather than claim knowledge outside its corpus.

## Trade-offs

Host Ollama saves Minikube memory, but adds host firewall/address availability as an operational dependency. Provider JSON enforcement ensures schema shape, not factual accuracy; evaluation and citation verification are separate obligations.
