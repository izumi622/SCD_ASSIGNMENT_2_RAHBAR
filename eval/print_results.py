#!/usr/bin/env python3
"""Print human-review summary from the actual UTF-8 RAHBAR evaluator JSON."""
import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print('Usage: python eval/print_results.py eval/results.json')
        return 2
    try:
        result = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        print(f'Failed to load results: {error}')
        return 2
    for key in ('questions', 'response_errors', 'recall_at_3', 'recall_at_5',
                'citation_validity', 'abstention_correctness'):
        print(f'{key}: {result.get(key)}')
    for q in result.get('per_question', []):
        answer = str(q.get('answer', '')).encode('ascii', 'backslashreplace').decode('ascii')
        citations = ', '.join(f"{c.get('source')} p.{c.get('page')}" for c in q.get('citations', []))
        print(f"\n{q.get('id')} [{q.get('type')}]: {answer[:600]}")
        print(f"  recall@5={q.get('recall_at_5')}; citation_validity={q.get('citation_validity')}; "
              f"grounded={q.get('answered_from_context')}; expected_text_present={q.get('expected_substring_present')}")
        print(f'  citations: {citations or "none"}')
        if q.get('error'):
            print(f"  ERROR: {q['error']}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
