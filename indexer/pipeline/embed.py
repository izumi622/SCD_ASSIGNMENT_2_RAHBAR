"""Batch embeddings using the one ConfigMap-pinned Ollama model."""
from __future__ import annotations
import httpx
from .config import IndexerSettings


def embed(texts: list[str], settings: IndexerSettings) -> list[list[float]]:
    if not texts: return []
    vectors: list[list[float]] = []
    with httpx.Client(timeout=httpx.Timeout(120.0, connect=10.0)) as http:
        for start in range(0,len(texts),8):
            batch = texts[start:start+8]
            r = http.post(settings.ollama_url.rstrip('/')+'/api/embed',
                          json={'model':settings.embed_model,'input':batch})
            r.raise_for_status()
            data = r.json().get('embeddings')
            if not isinstance(data,list) or len(data)!=len(batch):
                raise ValueError('Ollama embeddings count differs from input batch')
            for vector in data:
                if not isinstance(vector,list) or not vector or not all(isinstance(x,(int,float)) for x in vector):
                    raise ValueError('empty or malformed embedding')
            vectors.extend(data)
    if len({len(v) for v in vectors})!=1:
        raise ValueError('embedding dimensions differ')
    return vectors
