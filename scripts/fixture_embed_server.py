"""CI-only deterministic local /api/embed server.

Produces simple 768-dimensional bag-of-terms vectors, NOT semantic Ollama
embeddings. Never run it against the real university corpus or report fixture
retrieval scores as real RAG quality. It makes CI fixture indexing and query
reproducible without an external model or credential.
"""
from __future__ import annotations

from collections import Counter
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import re

MODEL = 'fixture-bow-768'
DIM = 768
STOP = frozenset('a an and are as at be by can did do does for from how i if in is it my of on or our the these this to up was were what when where which who will with you your'.split())
WORDS = re.compile(r'[a-z0-9]+', re.I)


def stem(word: str) -> str:
    word = word.lower()
    if word.endswith('ies') and len(word) > 5:
        return word[:-3]+'y'
    if word.endswith('ing') and len(word) > 6:
        return word[:-3]
    if word.endswith('ed') and len(word) > 5:
        return word[:-2]
    if word.endswith('s') and not word.endswith('ss') and len(word) > 4:
        return word[:-1]
    return word


def vector(text: str) -> list[float]:
    counts = Counter(stem(w) for w in WORDS.findall(text) if w.lower() not in STOP)
    floats = [0.0]*DIM
    for word, count in counts.items():
        digest = hashlib.sha256(word.encode()).digest()
        i = int.from_bytes(digest[:4], 'big') % DIM
        floats[i] += 1 + math.log(count)
    norm = math.sqrt(sum(x*x for x in floats))
    return [x/norm if norm else 0.0 for x in floats]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/healthz':
            return self._reply(404, {'error':'not found'})
        return self._reply(200, {'status':'ok'})

    def do_POST(self):
        if self.path != '/api/embed':
            return self._reply(404, {'error':'not found'})
        try:
            n = int(self.headers.get('Content-Length','0'))
            if n <= 0 or n > 1_000_000:
                raise ValueError('invalid body length')
            body = json.loads(self.rfile.read(n))
            if body.get('model') != MODEL:
                return self._reply(400, {'error':'fixture model mismatch'})
            texts = body.get('input')
            if isinstance(texts,str): texts=[texts]
            if not isinstance(texts,list) or not texts or len(texts)>100 or not all(isinstance(x,str) for x in texts):
                raise ValueError('expected nonempty strings')
            return self._reply(200, {'model':MODEL,'embeddings':[vector(t) for t in texts]})
        except (ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
            return self._reply(400, {'error':str(exc)})

    def _reply(self, status, payload):
        content=json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(content)))
        self.end_headers()
        self.wfile.write(content)


if __name__=='__main__':
    ThreadingHTTPServer(('0.0.0.0',11434),Handler).serve_forever()
