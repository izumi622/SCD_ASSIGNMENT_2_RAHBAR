#!/usr/bin/env python3
"""Evaluate a running RAHBAR instance and gate retrieval/citation/abstention regression.

A golden relevance entry must identify a chunk_id OR source with section/page.
Matches use actual API metadata; there is no source-only leniency. This avoids
counting a wrong section on the right document as a retrieval success.

Examples (from repository root):
  python eval/run_eval.py --api http://127.0.0.1:8000 --only q01,q13 --out eval/smoke.json
  python eval/run_eval.py --api http://127.0.0.1:8000 --require-mix --update-baseline
  python eval/run_eval.py --api http://127.0.0.1:8000 --require-mix
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import re
from pathlib import Path
import sys
import time

import httpx
import yaml

HERE = Path(__file__).resolve().parent
MAX_RECALL5_DROP = 0.05
MIN_CITATION_VALIDITY = 0.95
REQUIRED_ABSTENTION = 1.0
MINIMUM_BY_TYPE = {'ordinary': 8, 'version': 2, 'exact': 2, 'abstain': 2, 'injection': 1}


def load_golden(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    questions = data.get('questions') or []
    if not isinstance(questions, list) or not questions:
        raise ValueError(f'No questions in {path}')
    ids = set()
    for q in questions:
        if not isinstance(q, dict) or not q.get('question') or not q.get('id'):
            raise ValueError('Each golden entry must have an id and question')
        if q['id'] in ids:
            raise ValueError(f'Duplicate golden ID {q["id"]}')
        ids.add(q['id'])
        if not q.get('must_abstain') and not q.get('relevant'):
            raise ValueError(f'{q["id"]} must provide known relevant evidence')
        for ref in q.get('relevant') or []:
            if not isinstance(ref, dict):
                raise ValueError(f'{q["id"]}: relevance entries must be objects')
            if not (ref.get('chunk_id') or
                    (ref.get('source') and ('section' in ref or 'page' in ref))):
                raise ValueError(f'{q["id"]}: use chunk_id or source with section/page; no document-only matches')
    return questions


def validate_mix(questions: list[dict]) -> None:
    counts = Counter(q.get('type', 'ordinary') for q in questions)
    missing = [f'{t}: {counts.get(t, 0)}/{minimum}'
               for t, minimum in MINIMUM_BY_TYPE.items()
               if counts.get(t, 0) < minimum]
    if len(questions) < 15 or missing:
        raise ValueError('Golden set does not meet required 15-question mix: ' + ', '.join(missing))
    if sum(bool(q.get('must_abstain')) for q in questions) < 2:
        raise ValueError('At least two questions must have must_abstain: true')


def ask(client: httpx.Client, api: str, question: str) -> dict:
    response = client.post(f'{api.rstrip("/")}/api/ask', json={'question': question})
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict) or 'retrieved' not in result or 'citations' not in result:
        raise ValueError('Unexpected RAHBAR response shape')
    return result


def _matches(ref: dict, actual: dict) -> bool:
    if 'chunk_id' in ref:
        return ref['chunk_id'] == actual.get('chunk_id')
    if ref.get('source') != actual.get('source'):
        return False
    if 'section' in ref and ref['section'] != actual.get('section'):
        return False
    if 'page' in ref and ref['page'] != actual.get('page'):
        return False
    return True


def recall_at_k(relevant: list[dict], retrieved: list[dict], k: int) -> float | None:
    """Fraction of distinct golden evidence targets in first k retrieved passages."""
    if not relevant:
        return None
    # De-duplicate identical golden refs to avoid artificially inflating denominators.
    seen = set()
    refs = []
    for ref in relevant:
        ident = json.dumps(ref, sort_keys=True)
        if ident not in seen:
            refs.append(ref)
            seen.add(ident)
    first_k = (retrieved or [])[:k]
    return sum(any(_matches(ref, item) for item in first_k) for ref in refs) / len(refs)


def _citation_counts(response: dict) -> tuple[int, int]:
    cites = response.get('citations') or []
    retrieved = response.get('retrieved') or []
    valid = sum(any(cite.get('source') == item.get('source')
                    and cite.get('section') == item.get('section')
                    and cite.get('page') == item.get('page')
                    for item in retrieved)
                for cite in cites)
    return valid, len(cites)


def citation_validity(response: dict) -> float | None:
    valid, total = _citation_counts(response)
    return valid / total if total else None


# A literal substring check can flag semantically equivalent numerical answers,
# e.g. the known correct answer "2" when the golden reference says "two".
# This is ONLY an output expectation convenience, not retrieval/citation scoring.
_SIMPLE_NUMBERS = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
    'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18,
    'nineteen': 19, 'twenty': 20,
}


def expected_present(expect: str | None, answer: str | None) -> bool | None:
    """True for exact substring or equivalent single integer, without loosened matching.

    Do not use this as proof of a *correct* factual answer: a human must also
    inspect whether the evidence on the cited page supports the claim.
    """
    if not expect:
        return None
    expectation = str(expect).strip().casefold()
    actual = str(answer or '').casefold()
    # Pure integer expectations must use token-level matches: "2" is not "12".
    if expectation in _SIMPLE_NUMBERS:
        number = _SIMPLE_NUMBERS[expectation]
        return bool(re.search(r'\b' + expectation + r'\b', actual) or
                    re.search(r'(?<![\w.])' + str(number) + r'(?![\w.])', actual))
    if expectation.isdecimal() and int(expectation) <= 20:
        written = next((word for word, number in _SIMPLE_NUMBERS.items()
                        if number == int(expectation)), None)
        return bool(re.search(r'(?<![\w.])' + expectation + r'(?![\w.])', actual) or
                    (written and re.search(r'\b' + written + r'\b', actual)))
    return expectation in actual


def summarise(rows: list[dict]) -> dict:
    answerable = [row for row in rows if row['relevant']]
    by_type = {}
    for t in sorted({row['type'] for row in rows}):
        group = [row for row in rows if row['type'] == t and row['relevant']]
        by_type[t] = {
            'questions': len([row for row in rows if row['type'] == t]),
            'retrieval_scored': len(group),
            'recall_at_3': sum(recall_at_k(r['relevant'], r['response'].get('retrieved', []), 3) or 0
                               for r in group) / len(group) if group else None,
            'recall_at_5': sum(recall_at_k(r['relevant'], r['response'].get('retrieved', []), 5) or 0
                               for r in group) / len(group) if group else None,
        }
    citations_valid = sum(_citation_counts(r['response'])[0] for r in rows)
    citations_total = sum(_citation_counts(r['response'])[1] for r in rows)
    abstention_rows = [r for r in rows if r['must_abstain']]
    abstentions_correct = sum(r['response'].get('answered_from_context') is False
                              for r in abstention_rows)
    return {
        'recall_at_3': sum(recall_at_k(r['relevant'], r['response'].get('retrieved', []), 3) or 0
                           for r in answerable) / len(answerable) if answerable else None,
        'recall_at_5': sum(recall_at_k(r['relevant'], r['response'].get('retrieved', []), 5) or 0
                           for r in answerable) / len(answerable) if answerable else None,
        'by_type': by_type,
        'citation_validity': citations_valid / citations_total if citations_total else None,
        'valid_citations': citations_valid,
        'total_citations': citations_total,
        'abstention_correctness': abstentions_correct / len(abstention_rows) if abstention_rows else None,
        'abstentions_correct': abstentions_correct,
        'abstentions_total': len(abstention_rows),
        'response_errors': sum('error' in r for r in rows),
        'per_question': [{
            'id': row['id'], 'type': row['type'], 'seconds': row['seconds'],
            'recall_at_3': recall_at_k(row['relevant'], row['response'].get('retrieved', []), 3),
            'recall_at_5': recall_at_k(row['relevant'], row['response'].get('retrieved', []), 5),
            'citation_validity': citation_validity(row['response']),
            'must_abstain': row['must_abstain'],
            'answered_from_context': row['response'].get('answered_from_context'),
            'answer': row['response'].get('answer'),
            'expected_substring': row.get('expect'),
            'expected_substring_present': expected_present(row.get('expect'),
                                                           row['response'].get('answer')),
            'citations': row['response'].get('citations', []),
            'retrieved': row['response'].get('retrieved', []),
            **({'error': row['error']} if 'error' in row else {}),
        } for row in rows],
        'note': 'Recall is question-macro-averaged; source and section/page (or chunk ID) must match. '
                'Citation validity checks source, section and page against retrieved. '
                'Answer correctness and relevant evidence content still need manual review.',
    }


def gate(results: dict, baseline: dict | None) -> list[str]:
    failures = []
    if results.get('response_errors'):
        failures.append(f'{results["response_errors"]} API question(s) failed')
    # Retrieval and valid metadata do not demonstrate correct answers. An
    # answerable golden case must actually answer, satisfy its expected-content
    # check, and supply a citation to an evidence item it retrieved. This is a
    # deliberately conservative automated check; human review still matters.
    questions = results.get('per_question') or []
    if not questions:
        failures.append('No per-question answers available for content verification')
    for row in questions:
        if row.get('must_abstain'):
            # Abstention must not fabricate a citation.
            if row.get('answered_from_context') is not False or row.get('citations'):
                failures.append(f'{row.get("id", "?")}: must-abstain question answered or cited evidence')
            continue
        question_id = row.get('id', '?')
        if row.get('answered_from_context') is not True:
            failures.append(f'{question_id}: expected grounded answer; model abstained')
        if row.get('expected_substring_present') is not True:
            failures.append(f'{question_id}: expected-answer check failed')
        if row.get('citation_validity') != 1.0:
            failures.append(f'{question_id}: missing or invalid supporting citation')
    current_recall = results.get('recall_at_5')
    if current_recall is None:
        failures.append('No relevant questions were scored for recall@5')
    elif baseline is not None and baseline.get('recall_at_5') is not None:
        if current_recall < float(baseline['recall_at_5']) - MAX_RECALL5_DROP - 1e-12:
            failures.append(f'Recall@5 decreased from {baseline["recall_at_5"]:.3f} '
                            f'to {current_recall:.3f} (more than 5 percentage points)')
    citation_score = results.get('citation_validity')
    if citation_score is None or citation_score < MIN_CITATION_VALIDITY:
        failures.append('Citation validity is missing or below 95%')
    abstention = results.get('abstention_correctness')
    if abstention is None or abstention < REQUIRED_ABSTENTION:
        failures.append('Must-abstain correctness is missing or below 100%')
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description='Evaluate RAHBAR against a verified golden set')
    parser.add_argument('--api', required=True)
    parser.add_argument('--host', help='Host header for ingress, if needed')
    parser.add_argument('--golden', type=Path, default=HERE / 'golden.yaml')
    parser.add_argument('--baseline', type=Path, default=HERE / 'baseline.json')
    parser.add_argument('--out', type=Path, default=HERE / 'results.json')
    parser.add_argument('--update-baseline', action='store_true')
    parser.add_argument('--require-mix', action='store_true', help='Enforce assignment 15-question mix')
    parser.add_argument('--only', help='Comma-separated IDs for a smoke run (no gate or baseline update)')
    parser.add_argument('--timeout', type=float, default=390.0, help='API request read timeout in seconds')
    args = parser.parse_args()
    try:
        questions = load_golden(args.golden)
        if args.only:
            chosen = {q.strip() for q in args.only.split(',') if q.strip()}
            questions = [q for q in questions if q['id'] in chosen]
            if len(questions) != len(chosen):
                raise ValueError('One or more --only IDs do not exist')
            if args.update_baseline:
                raise ValueError('Cannot update baseline from a smoke subset')
        if args.require_mix:
            validate_mix(questions)
        for q in questions:
            if q.get('review_required') or q.get('needs_review'):
                raise ValueError(f'{q["id"]} has not been source-verified; review the draft before full evaluation')
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f'GOLDEN ERROR: {exc}', file=sys.stderr)
        return 2

    rows = []
    headers = {'Host': args.host} if args.host else {}
    with httpx.Client(timeout=httpx.Timeout(args.timeout, connect=15.0), headers=headers) as client:
        for q in questions:
            started = time.perf_counter()
            error = None
            try:
                response = ask(client, args.api, q['question'])
            except (httpx.HTTPError, ValueError) as exc:
                response = {'answer': '', 'citations': [], 'retrieved': [],
                            'answered_from_context': None}
                error = f'{type(exc).__name__}: {exc}'
            elapsed = round(time.perf_counter() - started, 2)
            row = {'id': q['id'], 'type': q.get('type', 'ordinary'),
                   'must_abstain': bool(q.get('must_abstain', False)),
                   'relevant': q.get('relevant') or [], 'expect': q.get('expect'),
                   'response': response, 'seconds': elapsed}
            if error:
                row['error'] = error
            rows.append(row)
            print(f'{q["id"]:<5} {elapsed:>7.2f}s  '
                  f'{"ERROR: " + error if error else q["question"][:75]}', flush=True)

    results = summarise(rows)
    results['golden'] = str(args.golden)
    results['questions'] = len(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'\nResults saved: {args.out}')

    if args.only:
        print('SMOKE RUN ONLY — no regression gate applied and no baseline written')
        return 1 if results['response_errors'] else 0
    try:
        baseline = json.loads(args.baseline.read_text(encoding='utf-8')) if args.baseline.exists() else None
    except (ValueError, OSError) as exc:
        print(f'BASELINE ERROR: {exc}', file=sys.stderr)
        return 2
    failures = gate(results, baseline)
    if failures:
        print('GATE FAILED:')
        for f in failures:
            print(' - ' + f)
        return 1
    print('GATE PASSED')
    if args.update_baseline:
        args.baseline.parent.mkdir(parents=True, exist_ok=True)
        args.baseline.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f'Baseline saved: {args.baseline}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
