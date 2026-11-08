"""Unit tests for the assignment's evaluation metrics and gate."""
import json
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('run_eval', Path(__file__).with_name('run_eval.py'))
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)

R = {'chunk_id': 'aaa', 'source': 'handbook.pdf', 'section': 'Attendance', 'page': 10, 'score': .9}
S = {'chunk_id': 'bbb', 'source': 'handbook.pdf', 'section': 'Graduation', 'page': 11, 'score': .8}
T = {'chunk_id': 'ccc', 'source': 'other.pdf', 'section': 'Policy', 'page': 2, 'score': .7}


def test_recall_topk_and_granularity():
    gold = [{'source': 'handbook.pdf', 'section': 'Attendance', 'page': 10},
            {'source': 'other.pdf', 'section': 'Policy', 'page': 2}]
    assert ev.recall_at_k(gold, [R, S, T], 1) == .5
    assert ev.recall_at_k(gold, [R, S, T], 3) == 1.0
    assert ev.recall_at_k(gold, [], 3) == 0.0
    assert ev.recall_at_k([], [R], 3) is None
    assert ev.recall_at_k([{'chunk_id': 'bbb'}], [R, S], 1) == 0.0
    assert ev.recall_at_k([{'chunk_id': 'bbb'}], [R, S], 2) == 1.0
    assert ev.recall_at_k([{'source': 'handbook.pdf', 'page': 11}], [R], 5) == 0.0


def test_citations_require_exact_section_and_page():
    data = {'retrieved': [R], 'citations': [
        {'source': 'handbook.pdf', 'section': 'Attendance', 'page': 10},
        {'source': 'handbook.pdf', 'section': 'Attendance', 'page': 11},
        {'source': 'handbook.pdf', 'section': 'Graduation', 'page': 10}]}
    assert ev.citation_validity(data) == 1/3
    assert ev.citation_validity({'retrieved': [R], 'citations': []}) is None


def test_summary_and_gates():
    rows = [
        {'id': 'q1','type':'ordinary','must_abstain':False,
         'relevant':[{'source':'handbook.pdf','page':10}], 'expect':'test',
         'response':{'answer':'test','retrieved':[R], 'citations':[{'source':'handbook.pdf',
             'section':'Attendance','page':10}], 'answered_from_context':True}, 'seconds':.1},
        {'id': 'q2','type':'abstain','must_abstain':True,'relevant':[], 'expect':None,
         'response':{'answer':'no evidence','retrieved':[T], 'citations':[], 'answered_from_context':False}, 'seconds':.1}
    ]
    report = ev.summarise(rows)
    assert report['recall_at_3'] == 1.0
    assert report['recall_at_5'] == 1.0
    assert report['citation_validity'] == 1.0
    assert report['abstention_correctness'] == 1.0
    assert not ev.gate(report, {'recall_at_5': 1.0})
    assert ev.gate(report, {'recall_at_5': 1.07})
    assert ev.gate({**report, 'abstention_correctness': 0.0}, None)
    assert ev.gate({**report, 'citation_validity': 0.94}, None)


def test_verified_draft_subset_and_mix():
    import yaml
    qs = yaml.safe_load(Path(__file__).with_name('golden.draft.yaml').read_text())['questions']
    assert len(qs) == 15
    ev.validate_mix(qs)
    assert [q['id'] for q in qs if q.get('review_required')] == ['q09', 'q10', 'q14']
    assert ev.recall_at_k([{'source': 'academic-rules-handbook-jun-2026.pdf', 'page': 10}],
                           [{'source': 'academic-rules-handbook-jun-2026.pdf', 'page': 10,
                             'section': 'Unheaded section'}], 1) == 1.0


def test_expected_number_equivalence_without_false_positives():
    assert ev.expected_present('two', '2') is True
    assert ev.expected_present('two', 'You can enroll in 2 courses.') is True
    assert ev.expected_present('2', 'You can enroll in two courses.') is True
    assert ev.expected_present('two', 'twelve') is False
    assert ev.expected_present('two', '12') is False
    assert ev.expected_present('two', '20') is False
    assert ev.expected_present('2', '12') is False
    assert ev.expected_present('two', '2.00') is False
    assert ev.expected_present('2.00', '2') is False
    assert ev.expected_present('20%', '20%') is True
    assert ev.expected_present('F/A', 'The student receives F/A.') is True
    assert ev.expected_present(None, 'any') is None


def test_numeric_expected_summary_does_not_change_citation_validation():
    rows = [{'id':'q08', 'type':'ordinary', 'must_abstain':False,
             'relevant':[{'source':'handbook.pdf', 'page':10}], 'expect':'two',
             'response':{'answer':'2', 'retrieved':[R],
                         'citations':[{'source':'handbook.pdf','section':'Attendance','page':10}],
                         'answered_from_context':True}, 'seconds':0.1}]
    result = ev.summarise(rows)
    assert result['per_question'][0]['expected_substring_present'] is True
    assert result['citation_validity'] == 1.0
    assert result['recall_at_5'] == 1.0


def test_answer_content_gate_rejects_false_perfect_retrieval():
    row={'id':'q07','type':'ordinary', 'must_abstain':False,
         'relevant':[{'source':'handbook.pdf','page':10}], 'expect':'2',
         'response':{'answer':'The retrieved evidence does not support a reliable numerical answer.',
                     'retrieved':[R], 'citations':[], 'answered_from_context':False},
         'seconds':.1}
    report=ev.summarise([row])
    assert report['recall_at_5']==1.0
    reasons=ev.gate(report, None)
    assert any('q07: expected grounded answer' in x for x in reasons)
    assert any('q07: expected-answer check failed' in x for x in reasons)
    assert any('q07: missing or invalid supporting citation' in x for x in reasons)

def test_grounded_expected_answer_keeps_gate_passing():
    row={'id':'q07', 'type':'ordinary','must_abstain':False,
         'relevant':[{'source':'handbook.pdf','page':10}], 'expect':'2',
         'response':{'answer':'two semesters', 'retrieved':[R],
                     'citations':[{'source':'handbook.pdf','section':'Attendance','page':10}],
                     'answered_from_context':True}, 'seconds':.1}
    report=ev.summarise([row])
    # Absent abstention questions still fail the overall gate, but not q07.
    assert not any('q07' in reason for reason in ev.gate(report, None))

def test_abstention_with_fabricated_citation_fails():
    row={'id':'q14', 'type':'abstain','must_abstain':True,
         'relevant':[], 'expect':None,
         'response':{'answer':'I do not know', 'retrieved':[R],
                     'citations':[{'source':'handbook.pdf','section':'Attendance','page':10}],
                     'answered_from_context':False},'seconds':.1}
    report=ev.summarise([row])
    assert any('q14' in reason for reason in ev.gate(report, None))
