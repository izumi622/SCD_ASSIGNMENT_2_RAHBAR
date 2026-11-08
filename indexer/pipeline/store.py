"""Single indexer writer. Upsert before removing obsolete chunks."""
from __future__ import annotations
from typing import Any
from .config import IndexerSettings
from .models import Chunk


def get_client(settings: IndexerSettings) -> Any:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    return chromadb.HttpClient(host=settings.chroma_host,port=settings.chroma_port,
                               settings=ChromaSettings(anonymized_telemetry=False))


def store(chunks: list[Chunk], vectors: list[list[float]], settings: IndexerSettings) -> int:
    if not chunks or len(chunks)!=len(vectors): raise ValueError('empty index or vector mismatch')
    dim = len(vectors[0]); model = settings.embed_model
    client=get_client(settings)
    metadata={'hnsw:space':'cosine','embed_model':model,'dimension':dim}
    try:
        col=client.get_collection(settings.collection)
        previous=col.metadata or {}
        if previous.get('embed_model') != model or int(previous.get('dimension',0)) != dim:
            # Allowed *once* when replacing the starter dummy index. Not an
            # atomic swap: the API readiness pin prevents mismatched answers.
            if previous.get('embed_model') != 'dummy-768':
                raise RuntimeError('Existing real index uses another embedding model/dimension; '
                                   'migrate through a controlled collection swap')
            client.delete_collection(settings.collection)
            col=client.create_collection(settings.collection,metadata=metadata)
    except Exception as exc:
        # Never reinterpret an incompatible index as a missing index.
        if not type(exc).__name__ in {'NotFoundError','InvalidCollectionException'} and            'does not exist' not in str(exc).lower() and 'not found' not in str(exc).lower():
            raise
        col=client.create_collection(settings.collection,metadata=metadata)
    wanted={c.id for c in chunks}
    for start in range(0,len(chunks),100):
        batch=chunks[start:start+100]
        col.upsert(ids=[c.id for c in batch],documents=[c.text for c in batch],
                   embeddings=vectors[start:start+100],metadatas=[c.metadata() for c in batch])
    old_ids=col.get(include=[])['ids']
    stale=[id for id in old_ids if id not in wanted]
    for start in range(0,len(stale),100): col.delete(ids=stale[start:start+100])
    # Semantic cache and generation responses were computed on old passages.
    try:
        import redis
        r=redis.Redis(host=settings.redis_host,port=settings.redis_port,socket_connect_timeout=1,socket_timeout=1)
        for key in r.scan_iter('rahbar:cache:*',count=100): r.delete(key)
        r.incr('rahbar:index:revision'); r.close()
    except Exception:
        # Cache failure is visible to logs, but not allowed to silently serve
        # an outdated answer in a fully enabled deployment (address in phase 3).
        raise RuntimeError('Cache invalidation failed after successful indexing')
    return int(col.count())
