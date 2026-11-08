from app.config import Settings
from app.retrieval.chroma import ChromaRetriever, _lexical_coverage
from app.schemas import Passage, Answer, Citation
from app.services.answer import answer_question


def test_lexical_inflections():
    question = "Who can condone absence for genuine reasons?"
    evidence = "Absence may be condoned by the Head of Department for genuine reasons."
    assert _lexical_coverage(question, evidence) > 0.6


class FakeCollection:
    metadata={'embed_model':'nomic-embed-text','dimension':2}
    def count(self): return 100
    def query(self, **kwargs):
        assert kwargs['n_results'] >= 30
        return {'ids':[['a','b']],
                'documents':[['General attendance requirements mention student classes.',
                              'Absence may be condoned by the Head of Department for genuine reasons.']],
                'metadatas':[[{'source':'student.pdf','section':'General','page':30},
                              {'source':'policy.pdf','section':'Unheaded section','page':10}]],
                'distances':[[0.3, 0.38]]}


def test_lexical_reranking_can_rescue_exact_policy_passage(monkeypatch):
    retriever=ChromaRetriever(Settings(retriever='chroma'))
    monkeypatch.setattr(retriever,'_collection',lambda: FakeCollection())
    monkeypatch.setattr(retriever,'_embed',lambda q:[0.1,0.2])
    got=retriever.retrieve('Who can condone absence for genuine reasons?',k=2)
    assert got[0].source=='policy.pdf'
    assert got[0].score==0.62  # original vector similarity not inflated


class Retriever:
    name='fake'
    def retrieve(self,q,k):
        return [Passage(chunk_id='x',text='Two summer courses.',source='policy.pdf',
                        section='Unheaded section',page=9,score=0.81)]


class Provider:
    name='stub'
    def __init__(self, citation): self.citation=citation
    def generate(self,q,ps):
        return Answer(reasoning='evidence',answer='Two courses are permitted.',
                      citations=[self.citation],answered_from_context=True,confidence='high')


def test_section_alias_normalized_only_when_source_and_page_match():
    result=answer_question('Maximum summer courses?',Retriever(),
         Provider(Citation(source='policy.pdf',section='Rule 1.19',page=9)),Settings())
    assert result.answered_from_context
    assert result.citations[0].section=='Unheaded section'


def test_wrong_page_still_rejected():
    result=answer_question('Maximum summer courses?',Retriever(),
         Provider(Citation(source='policy.pdf',section='Rule 1.19',page=10)),Settings())
    assert not result.answered_from_context
    assert result.citations==[]


def test_wrong_source_still_rejected():
    result=answer_question('Maximum summer courses?',Retriever(),
         Provider(Citation(source='invented.pdf',section='Rule 1.19',page=9)),Settings())
    assert not result.answered_from_context
    assert result.citations==[]
