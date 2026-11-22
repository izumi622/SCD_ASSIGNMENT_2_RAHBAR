#!/usr/bin/env python3
"""Read-only live RAHBAR chunking ablation against an existing Minikube deployment.

Run from repository root:
    "C:\\msys64\\ucrt64\\bin\\python3.exe" rahbar_chunk_ablation_metrics.py

Requires PyYAML installed locally (as for eval/run_eval.py), minikube, and the
already-running API/Chroma/Ollama services. No collections or cache keys are changed.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    try:
        import yaml
    except ImportError:
        print('ERROR: PyYAML is not installed in this Python. Use the same environment as eval/run_eval.py.', file=sys.stderr)
        return 2

    golden_path = Path('eval/golden.yaml')
    if not golden_path.exists():
        print('ERROR: Run this script from the RAHBAR project root (eval/golden.yaml not found).', file=sys.stderr)
        return 2
    doc = yaml.safe_load(golden_path.read_text(encoding='utf-8'))
    questions = doc['questions']
    if len(questions) != 15:
        print(f'WARNING: Current golden set has {len(questions)} questions, not 15.')

    # The embedded Python runs in an existing API container and imports its real
    # ChromaRetriever, including the hybrid lexical rerank and version filter.
    # No kubectl apply, no index writes, and no changes to API pod environment.
    golden_literal = repr(json.dumps(questions, ensure_ascii=True))
    remote = '''
import json
import sys
from dataclasses import replace
import chromadb
from app.config import get_settings
from app.retrieval.chroma import ChromaRetriever

questions = json.loads(GOLDEN_LITERAL)
base_settings = get_settings()
client = chromadb.HttpClient(host=base_settings.chroma_host, port=base_settings.chroma_port)
collections = [
    ('200/25', 'rahbar_ablation_200_25'),
    ('400/50', 'rahbar'),
    ('600/75', 'rahbar_ablation_600_75'),
]

def matches(expected, actual):
    if 'chunk_id' in expected:
        return expected['chunk_id'] == actual.chunk_id
    return (
        expected.get('source') == actual.source
        and ('section' not in expected or expected['section'] == actual.section)
        and ('page' not in expected or expected['page'] == actual.page)
    )

out = []
for label, name in collections:
    print('Checking', name, flush=True)
    coll = client.get_collection(name)
    data = coll.get(include=['documents'])
    chunks = coll.count()
    stored_words = sum(len(text.split()) for text in (data.get('documents') or []) if text)
    retriever = ChromaRetriever(replace(base_settings, collection=name))
    rows = []
    for q in questions:
        relevant = q.get('relevant') or []
        if not relevant:
            continue  # Abstention has no known relevant source for recall scoring.
        found = retriever.retrieve(q['question'], 5)
        # Matches eval/run_eval.py: macro averaging of per-question relevant refs.
        def recall(k):
            unique = list({json.dumps(x, sort_keys=True): x for x in relevant}.values())
            return sum(any(matches(ref, passage) for passage in found[:k]) for ref in unique) / len(unique)
        rows.append({'id': q['id'], 'type': q.get('type', 'ordinary'),
                     'recall_at_3': recall(3), 'recall_at_5': recall(5),
                     'top5': [{'source': p.source, 'section': p.section,
                               'page': p.page, 'score': p.score} for p in found]})
    avg3 = sum(r['recall_at_3'] for r in rows) / len(rows)
    avg5 = sum(r['recall_at_5'] for r in rows) / len(rows)
    result = {'setting': label, 'collection': name, 'chunks': chunks,
              'stored_chunk_words': stored_words,
              'retrieval_questions': len(rows), 'recall_at_3': avg3,
              'recall_at_5': avg5, 'per_question': rows}
    out.append(result)
    print('RESULT', label, 'chunks=', chunks, 'stored_words=', stored_words,
          'recall@5=', format(avg5, '.4f'), flush=True)
print('RAHBAR_ABLATION_JSON=' + json.dumps(out, ensure_ascii=True), flush=True)
'''.replace('GOLDEN_LITERAL', golden_literal)

    cmd = ['minikube', 'kubectl', '--', 'exec', '-i', '-n', 'rahbar',
           'deployment/api', '--', 'python', '-']
    print('Read-only evaluation of 3 existing Chroma collections against the local golden set.')
    print('This may take several minutes; leave Ollama running.', flush=True)
    try:
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding='utf-8', errors='replace')
    except OSError as exc:
        print('Failed to launch Minikube command:', exc, file=sys.stderr)
        return 2
    assert process.stdin and process.stdout
    process.stdin.write(remote)
    process.stdin.close()
    raw = None
    for line in process.stdout:
        line = line.rstrip('\r\n')
        if line.startswith('RAHBAR_ABLATION_JSON='):
            raw = line.partition('=')[2]
        else:
            print(line, flush=True)
    rc = process.wait()
    if rc != 0 or raw is None:
        print(f'ERROR: Evaluation failed (exit code {rc}); no report written.', file=sys.stderr)
        return 1

    results = json.loads(raw)
    baseline_words = next((row['stored_chunk_words'] for row in results if row['setting'] == '400/50'), None)
    report_path = Path('docs/CHUNKING-ABLATION-RESULTS.md')
    json_path = Path('docs/chunking-ablation-results.json')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps({'golden': str(golden_path), 'results': results},
                                    indent=2) + '\n', encoding='utf-8')
    table = [
        '# RAHBAR chunking ablation — live retrieval measurements',
        '',
        'All three indexes use the same nine-document real FAST-NUCES corpus and the same',
        'Ollama embedding model. Read-only evaluation imported the deployed API\'s real',
        '`ChromaRetriever` and tested the answerable golden questions for retrieved',
        'source, section, and page metadata. The two must-abstain questions have no',
        'golden relevant passage and are not included in retrieval Recall@5.',
        '',
        '| Chunk size / overlap (words) | Chunks | Indexed chunk words | Indexed words vs baseline | Recall@3 | Recall@5 |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    for row in results:
        ratio = row['stored_chunk_words'] / baseline_words if baseline_words else 0
        table.append(f"| {row['setting']} | {row['chunks']} | {row['stored_chunk_words']:,} | "
                     f"{ratio:.3f}x | {row['recall_at_3']:.4f} | {row['recall_at_5']:.4f} |")
    table += [
        '',
        '**Measurement limitations:**',
        '- `Indexed chunk words` counts words from stored chunks, including repeated overlap.',
        '- `Indexed words vs baseline` is a relative measure. It is **not** the required',
        '  source-normalized storage amplification, which needs the original extracted',
        '  cleaned corpus word count as the denominator.',
        '- These are retrieval-only measurements, not uncached LLM answer accuracy.',
        '- A previous 400/50 golden evaluation also tested generation and abstention;',
        '  do not silently equate that result with this retrieval-only comparison.',
        '- Raw per-question results and the five retrieved passages are in',
        '  `docs/chunking-ablation-results.json`.',
        '',
    ]
    report_path.write_text('\n'.join(table), encoding='utf-8')
    print('\nSaved:', json_path)
    print('Saved:', report_path)
    print('NOTE: Source-normalized storage amplification still requires source word count.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
