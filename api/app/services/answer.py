"""Grounding and safety checks around a pluggable Retriever and LLM provider."""
from __future__ import annotations
import logging
import time
from ..config import Settings
from ..logjson import request_id_var
from ..providers.llm.base import LLMProvider
from ..retrieval.base import Retriever
from ..schemas import Answer, AskResponse, RetrievedRef, Citation
from ..routes.metrics import (RETRIEVAL_LATENCY, GENERATION_LATENCY, ABSTENTIONS,
                              FALLBACKS, CACHE_LOOKUPS, track_cache_hit)
from .cache import SemanticCache, cacheable
from .quantity import best_quantitative_evidence, quantity_supported, grounded_extractive_quantity_answer

log=logging.getLogger('rahbar.answer')

def _abstain(message: str) -> Answer:
    return Answer(reasoning='not supported by retrieved passages',answer=message,
                  citations=[],answered_from_context=False,confidence='low')

def answer_question(question: str,retriever: Retriever,provider: LLMProvider,settings: Settings) -> AskResponse:
    cache = None
    use_cache = settings.retriever == 'chroma' and provider.name != 'stub' and cacheable(question)
    if use_cache:
        try:
            cache = SemanticCache(settings)
            result = cache.lookup(question)
            track_cache_hit(result is not None)
            if result is not None:
                result.request_id = request_id_var.get()
                result.cached = True
                cache.close()
                return result
        except Exception:
            CACHE_LOOKUPS.labels(result='error').inc()
            log.warning('semantic cache lookup failed',exc_info=True)
            if cache: cache.close()
            cache = None
    else:
        CACHE_LOOKUPS.labels(result='skip').inc()
    begin=time.perf_counter()
    try:
        passages=retriever.retrieve(question,k=settings.top_k)
    except Exception:
        log.exception('retrieval failed')
        FALLBACKS.inc()
        passages=[]
        answer=_abstain('Document retrieval is temporarily unavailable. Please try again.')
    else:
        RETRIEVAL_LATENCY.observe(time.perf_counter()-begin)
        relevant=[p for p in passages if p.score >= settings.relevance_floor]
        if not relevant:
            answer=_abstain('The indexed documents do not contain enough information to answer this question.')
        else:
            start=time.perf_counter()
            try:
                answer=provider.generate(question,relevant)
            except Exception:
                log.exception('generation failed')
                FALLBACKS.inc()
                answer=_abstain('Answer generation is temporarily unavailable. Please try again.')
            GENERATION_LATENCY.observe(time.perf_counter()-start)
            # Never pass model-supplied citations through without checking the retrieved evidence.
            valid={(p.source,p.section,p.page) for p in relevant}
            checked=[]
            invalid=[]
            for c in answer.citations:
                if (c.source,c.section,c.page) in valid:
                    checked.append(c)
                    continue
                # The text often contains "Rule 1.19" even when the indexer's
                # section metadata says "Unheaded section". Accept only an
                # unambiguous *source + PDF page* already in retrieved evidence;
                # do not invent or substitute a source, page, or missing cite.
                matches={(p.source,p.section,p.page) for p in relevant
                         if p.source == c.source and p.page == c.page and p.page is not None}
                if len(matches) == 1:
                    source,section,page = next(iter(matches))
                    checked.append(Citation(source=source,section=section,page=page))
                    log.info('normalized citation section to retrieved metadata',
                             extra={'source':source,'page':page})
                else:
                    invalid.append(c)
            if invalid or (answer.answered_from_context and not checked):
                FALLBACKS.inc()
                log.warning('model citations failed evidence validation',
                            extra={'invalid_count':len(invalid),'cited_count':len(answer.citations),
                                   'invalid_citations':[c.model_dump() for c in invalid],
                                   'accepted_citations':[c.model_dump() for c in checked],
                                   'allowed_evidence':[{'source':p.source,'section':p.section,'page':p.page} for p in relevant]})
                answer=_abstain('The generated answer could not be grounded in the retrieved documents.')
            elif answer.answered_from_context:
                answer=answer.model_copy(update={'citations':checked})
                if not quantity_supported(question, answer, checked, relevant):
                    log.warning('unsupported numeric claim; retry with focused evidence',
                                extra={'answer':answer.answer,
                                       'citations':[c.model_dump() for c in checked]})
                    focus=best_quantitative_evidence(question, relevant)
                    retry = None
                    if focus is not None:
                        best, snippet, _ = focus
                        try:
                            retry = provider.generate(question, [best])
                        except Exception:
                            log.exception('focused quantity generation failed')
                        if retry is not None:
                            # A focused retry may cite only the single source actually supplied.
                            retry_cites=[]
                            for c in retry.citations:
                                if c.source == best.source and c.page == best.page:
                                    retry_cites.append(Citation(source=best.source,
                                                                section=best.section,page=best.page))
                            if (retry.answered_from_context and retry_cites and
                                    len(retry_cites) == len(retry.citations) and
                                    quantity_supported(question, retry, retry_cites, [best])):
                                answer=retry.model_copy(update={'citations':retry_cites})
                                log.info('focused numeric retry grounded in evidence',
                                         extra={'source':best.source,'page':best.page})
                            else:
                                retry = None
                    if retry is None:
                        # Qwen can fail even on an explicit, safely retrieved limit.
                        # Use a literal high-confidence sentence instead of inventing
                        # an answer or unnecessarily abstaining. The citation must be
                        # one of the original retrieved (source, section, page) tuples.
                        extracted = grounded_extractive_quantity_answer(question, relevant)
                        if extracted is not None:
                            answer = extracted
                            log.info('extractive numeric fallback used',
                                     extra={'source':answer.citations[0].source,
                                            'page':answer.citations[0].page})
                        else:
                            FALLBACKS.inc()
                            answer=_abstain('The retrieved evidence does not support a reliable numerical answer.')
            if not answer.answered_from_context:
                answer=answer.model_copy(update={'citations':[]})
    if not answer.answered_from_context:
        ABSTENTIONS.inc()
    log.info('answered',extra={'retriever':retriever.name,'provider':provider.name,'top_k':settings.top_k,
             'chunk_ids':[p.chunk_id for p in passages],
             'scores':[round(p.score,4) for p in passages],
             'answered_from_context':answer.answered_from_context})
    response = AskResponse(request_id=request_id_var.get(),answer=answer.answer,
                       citations=answer.citations,answered_from_context=answer.answered_from_context,
                       confidence=answer.confidence,
                       retrieved=[RetrievedRef(chunk_id=p.chunk_id,source=p.source,
                                   section=p.section,page=p.page,score=p.score) for p in passages],
                       provider=provider.name)
    if cache:
        try:
            # Never cache abstentions, ungrounded responses or replies to follow-ups.
            if response.answered_from_context and response.citations:
                cache.store(question,response)
        except Exception:
            log.warning('semantic cache write failed',exc_info=True)
        finally:
            cache.close()
    return response
