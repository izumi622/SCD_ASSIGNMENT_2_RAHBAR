"""Regression tests for conservative literal numeric-policy extraction."""
from app.schemas import Passage, Answer, Citation
from app.config import Settings
from app.services.quantity import grounded_extractive_quantity_answer
from app.services.answer import answer_question

QUESTION='For how many semesters may a student normally request a semester freeze?'
SOURCE='academic-rules-handbook-jun-2026.pdf'
P1=Passage(chunk_id='prefix', source=SOURCE, section='Unheaded section',
    page=22, score=.837,
    text='Freezing of Semester 4.18 | A student may request freezing of his/her admission for up to')
P2=Passage(chunk_id='suffix', source=SOURCE,
    section='2 semesters along with prescribed Semester Freeze charges.',
    page=22, score=.826,
    text='2 semesters along with prescribed Semester Freeze charges. Freezing of first two semesters of BS degree are not allowed.')


def test_literal_answer_comes_from_exact_same_page_evidence():
    result=grounded_extractive_quantity_answer(QUESTION,[P1,P2])
    assert result is not None
    assert result.answered_from_context
    assert result.answer.startswith('A student may request freezing')
    assert 'up to 2 semesters' in result.answer
    assert result.citations == [Citation(source=SOURCE,section='Unheaded section',page=22)]


def test_cannot_merge_across_pages_or_sources():
    assert grounded_extractive_quantity_answer(QUESTION,[P1,P2.model_copy(update={'page':23})]) is None
    assert grounded_extractive_quantity_answer(QUESTION,[P1,P2.model_copy(update={'source':'other.pdf'})]) is None


def test_unrelated_question_cannot_use_matching_number():
    q='How many courses can I register for in summer semester?'
    assert grounded_extractive_quantity_answer(q,[P1,P2]) is None


def test_no_retrieved_evidence_means_no_extractive_answer():
    assert grounded_extractive_quantity_answer(QUESTION,[]) is None


def test_fallback_after_two_invalid_model_quantities():
    class Retriever:
        name='test'
        def retrieve(self,question,k): return [P1,P2]
    class Provider:
        name='stub'
        def __init__(self):self.calls=0
        def generate(self,question,passages):
            self.calls+=1
            p=passages[0]
            return Answer(reasoning='Incorrect',answer='40 semesters',
                citations=[Citation(source=p.source,section=p.section,page=p.page)],
                answered_from_context=True,confidence='low')
    provider=Provider()
    result=answer_question(QUESTION,Retriever(),provider,Settings())
    assert provider.calls == 2
    assert result.answered_from_context
    assert 'up to 2 semesters' in result.answer
    assert result.citations[0].page == 22


def test_does_not_fabricate_answer_when_text_lacks_limit():
    vague=Passage(chunk_id='vague',source=SOURCE,section='Unheaded section',page=22,
        score=.99,text='Students may request a semester freeze after approval.')
    assert grounded_extractive_quantity_answer(QUESTION,[vague]) is None
