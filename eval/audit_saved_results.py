"""Audit a saved run without querying Ollama or modifying the baseline."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from run_eval import gate

path=Path(sys.argv[1] if len(sys.argv)>1 else 'eval/results.json')
report=json.loads(path.read_text(encoding='utf-8'))
rows=report.get('per_question',[])
print('Questions:',report.get('questions',len(rows)))
print('Retrieval recall@5:',report.get('recall_at_5'))
print('Citation metadata validity:',report.get('citation_validity'))
print('Abstention correctness:',report.get('abstention_correctness'))
print('Response errors:',report.get('response_errors'))
accepted=[]
for r in rows:
    ok= (r.get('answered_from_context') is False and not r.get('citations')) if r.get('must_abstain') else (r.get('answered_from_context') is True and r.get('expected_substring_present') is True and r.get('citation_validity')==1.0)
    if ok:
        accepted.append(r.get('id'))
    else:
        print('NEEDS REVIEW:',r.get('id'), 'answer=',ascii(r.get('answer'))[:180],
              'grounded=',r.get('answered_from_context'), 'expected=',r.get('expected_substring_present'), 'citation=',r.get('citation_validity'))
print('Automated answer checks:',len(accepted),'/',len(rows))
failures=gate(report,None)
if failures:
    print('STRICT GATE FAILED:')
    for f in failures: print(' -',f)
    sys.exit(1)
print('STRICT GATE PASSED (manual factual checks still required)')
