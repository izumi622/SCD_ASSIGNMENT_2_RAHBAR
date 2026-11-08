"""Fast offline checks for the Ollama timeout and output-bounding patch."""
from __future__ import annotations
from app.config import Settings
from app.schemas import Passage
from app.providers.llm.ollama import OllamaProvider
import app.providers.llm.ollama as module


def test_generation_timeout_and_output_options(monkeypatch):
    recorded = {}
    class FakeResponse:
        def raise_for_status(self): pass
        def json(self):
            return {'message': {'content': '{"reasoning":"evidence","answer":"Attendance is 80 percent.","citations":[{"source":"rules.pdf","section":"Attendance","page":5}],"answered_from_context":true,"confidence":"high"}'}}
    class FakeHTTP:
        def __init__(self, **kwargs): recorded['timeout'] = kwargs['timeout']
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, json):
            recorded['request'] = json
            return FakeResponse()
    monkeypatch.setattr(module.httpx, 'Client', FakeHTTP)
    monkeypatch.setenv('OLLAMA_READ_TIMEOUT','240')
    p = Passage(chunk_id='c1',text='Attendance is 80 percent',source='rules.pdf',section='Attendance',page=5,score=.8)
    result = OllamaProvider(Settings(llm_model='qwen2.5:7b')).generate('Minimum attendance?', [p])
    assert result.answered_from_context is True
    assert recorded['timeout'].read == 240
    assert recorded['request']['options']['num_predict'] == 420
    assert recorded['request']['options']['num_ctx'] == 4096
    assert recorded['request']['model'] == 'qwen2.5:7b'
    assert recorded['request']['stream'] is False
    assert recorded['request']['format']['type'] == 'object'
