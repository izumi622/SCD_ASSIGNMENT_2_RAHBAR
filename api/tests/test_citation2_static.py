from pathlib import Path
import re

BASE = Path(__file__).resolve().parents[1]

def test_single_fact_citation_instruction():
    provider = (BASE / 'app/providers/llm/ollama.py').read_text()
    assert 'select ONE best supporting EVIDENCE block' in provider
    assert 'copy source, section and page exactly' in provider

def test_validator_still_fail_closed():
    validator = (BASE / 'app/services/answer.py').read_text()
    assert 'if invalid or (answer.answered_from_context and not checked)' in validator
    assert "_abstain('The generated answer could not be grounded in the retrieved documents.')" in validator
    assert "'invalid_citations':[c.model_dump() for c in invalid]" in validator

def test_deployment_image_updated():
    yaml = (BASE.parent / 'k8s/base/api.yaml').read_text()
    # Image tags advance during bug fixes; assert a versioned RAHBAR image is deployed.
    assert re.search(r'(?m)^\s*image:\s*rahbar-api:(?!latest\b|starter\b)[\w.-]+\s*$', yaml)
    assert 'memory: 768Mi' in yaml
