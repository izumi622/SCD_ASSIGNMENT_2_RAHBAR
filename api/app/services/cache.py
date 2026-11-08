"""Small, measured semantic-cache implementation; Redis persistence is in Kubernetes."""
from __future__ import annotations
import hashlib
import json
import math
import os
import re
import httpx
from ..config import Settings
from ..schemas import AskResponse

_FOLLOWUP = re.compile(r'^(?:and |also |what about|how about|why (?:is|does) that|tell me more|what do you mean|it |they |this |that )',re.I)
_HISTORY = re.compile(r'\b(?:2023|2022|2021|old|historical|superseded|previous)\b',re.I)

def cacheable(question: str) -> bool:
    return not _FOLLOWUP.search(question.strip()) and not _HISTORY.search(question)

def _cosine(a: list[float],b: list[float]) -> float:
    if len(a)!=len(b) or not a: return -1
    denom=math.sqrt(sum(x*x for x in a))*math.sqrt(sum(x*x for x in b))
    return sum(x*y for x,y in zip(a,b))/denom if denom else -1

class SemanticCache:
    def __init__(self,settings: Settings):
        self.settings=settings
        import redis
        self.conn=redis.Redis(host=settings.redis_host,port=settings.redis_port,
                              socket_connect_timeout=2,socket_timeout=2)
        revision=self.conn.get('rahbar:index:revision')
        self.revision=(revision.decode() if revision is not None else '0') + ':' + os.environ.get('RAHBAR_RETRIEVAL_REV', 'quantity1')
        self.vec: list[float] | None=None

    def close(self): self.conn.close()

    def _embedding(self,question: str) -> list[float]:
        if self.vec is None:
            with httpx.Client(timeout=httpx.Timeout(45,connect=5)) as http:
                resp=http.post(self.settings.ollama_url.rstrip('/')+'/api/embed',
                               json={'model':self.settings.embed_model,'input':[question]})
                resp.raise_for_status()
                vectors=resp.json()['embeddings']
                if len(vectors)!=1 or not vectors[0]: raise ValueError('no question embedding')
                self.vec=vectors[0]
        return self.vec

    def lookup(self,question: str) -> AskResponse | None:
        vec=self._embedding(question)
        best=None;score=-1.0
        for key in self.conn.scan_iter(match=f'rahbar:cache:{self.revision}:*',count=50):
            raw=self.conn.get(key)
            if not raw: continue
            item=json.loads(raw)
            if item.get('model')!=self.settings.embed_model: continue
            val=_cosine(vec,item['vector'])
            if val>score: score=val;best=item
        if best is not None and score >= self.settings.cache_threshold:
            return AskResponse.model_validate(best['response'])
        return None

    def store(self,question: str,response: AskResponse) -> None:
        vec=self._embedding(question)
        key='rahbar:cache:'+self.revision+':'+hashlib.sha256(question.lower().encode()).hexdigest()[:20]
        data={'model':self.settings.embed_model,'vector':vec,'response':response.model_dump()}
        self.conn.set(key,json.dumps(data),ex=24*3600)
