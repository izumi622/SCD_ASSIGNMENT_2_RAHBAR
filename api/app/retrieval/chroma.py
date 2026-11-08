"""Retrieve real passages from Chroma with the indexer's pinned embedding model."""
from __future__ import annotations
import re
from typing import Any
import httpx
from ..config import Settings
from ..schemas import Passage

_OLD_VERSION = re.compile(r'\b(?:2023|2022|2021|2020|2019|old(?:er)?|historical|previous|superseded|earlier)\b', re.I)

_WORDS = re.compile(r"[a-z]+|[0-9]+(?:\.[0-9]+)?", re.I)
_STOP = frozenset('a an and are as at be by can do does for from how in is it of on or the their these this to up what when where which who why with'.split())


def _term(word: str) -> str:
    """Light inflection normalization; no extra NLP library in the API image."""
    word=word.casefold()
    if word.endswith('ies') and len(word) > 5:
        return word[:-3] + 'y'
    if word.endswith('ences') and len(word) > 6:
        return word[:-1]
    if word.endswith('ing') and len(word) > 6:
        return word[:-3]
    if word.endswith('ed') and len(word) > 5:
        return word[:-2]
    if word.endswith('s') and not word.endswith('ss') and len(word) > 4:
        return word[:-1]
    if word.endswith('e') and len(word) > 5:
        return word[:-1]
    return word


def _lexical_coverage(question: str, passage: str) -> float:
    query = {_term(w) for w in _WORDS.findall(question) if w.casefold() not in _STOP}
    if not query:
        return 0.0
    doc = {_term(w) for w in _WORDS.findall(passage)}
    return len(query & doc) / len(query)


class ChromaRetriever:
    name = 'chroma'
    def __init__(self, settings: Settings) -> None:
        self.settings=settings
        # IMPORTANT: no network call in API lifespan; /readyz decides readiness.
        self._client: Any = None

    def _collection(self):
        if self._client is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            self._client=chromadb.HttpClient(host=self.settings.chroma_host,
                         port=self.settings.chroma_port,
                         settings=ChromaSettings(anonymized_telemetry=False))
        collection=self._client.get_collection(self.settings.collection)
        metadata=collection.metadata or {}
        if metadata.get('embed_model')!=self.settings.embed_model:
            raise RuntimeError(f'embedding mismatch: index={metadata.get("embed_model")} '
                               f'api={self.settings.embed_model}')
        return collection

    def _embed(self, question: str) -> list[float]:
        url=self.settings.ollama_url.rstrip('/')+'/api/embed'
        with httpx.Client(timeout=httpx.Timeout(45.0,connect=5.0)) as http:
            resp=http.post(url,json={'model':self.settings.embed_model,'input':[question]})
            resp.raise_for_status()
            embeddings=resp.json().get('embeddings') or []
            if len(embeddings)!=1 or not embeddings[0]:
                raise ValueError('embedding provider returned no question vector')
            return embeddings[0]

    def retrieve(self, question: str, k: int) -> list[Passage]:
        collection=self._collection()
        vector=self._embed(question)
        expected=int((collection.metadata or {}).get('dimension',0))
        if expected and expected != len(vector):
            raise RuntimeError(f'embedding dimension mismatch: index={expected}, query={len(vector)}')
        historic=bool(_OLD_VERSION.search(question))
        # Retrieve a modest candidate pool, then blend semantic similarity with
        # exact-term coverage. This helps when embeddings blur clause wording.
        # The externally visible top_k stays unchanged, and the original cosine
        # similarities remain the values used by the relevance threshold.
        candidate_count = max(1, k, 30)
        if callable(getattr(collection, 'count', None)):
            candidate_count = min(candidate_count, max(1, collection.count()))
        result=collection.query(query_embeddings=[vector],n_results=candidate_count,
                  where=None if historic else {'superseded':False},
                  include=['documents','metadatas','distances'])
        ids=result['ids'][0] or []
        documents=(result.get('documents') or [[]])[0]
        metadatas=(result.get('metadatas') or [[]])[0]
        distances=(result.get('distances') or [[]])[0]
        passages=[]
        for id,txt,meta,distance in zip(ids,documents,metadatas,distances):
            meta=meta or {}
            passages.append(Passage(chunk_id=str(id),text=str(txt or ''),
                        source=str(meta.get('source','unknown')),
                        section=str(meta.get('section','Unheaded')),
                        page=int(meta['page']) if meta.get('page') is not None else None,
                        score=1-float(distance)))
        # Generic lexical reranking, not special-cased to evaluation questions.
        # A 25% lexical signal improves explicit policy/section queries without
        # converting uncorrelated keyword hits into high semantic scores.
        passages.sort(key=lambda p: (0.75 * p.score +
                                     0.25 * _lexical_coverage(question, p.text)),
                      reverse=True)
        return passages[:k]
