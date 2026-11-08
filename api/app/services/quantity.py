"""Evidence-derived checks for simple quantitative answers.

These helpers contain no university-specific values or hard-coded golden answers.
They can never create a citation for a source that was not retrieved.
"""
from __future__ import annotations

import re
from ..schemas import Answer, Passage, Citation

_QUANTITY_QUESTION = re.compile(
    r'\b(?:how many|how much|what percentage|what percent|what number|maximum|minimum|'
    r'how long|how old|how often|how many times|how many courses|what cgpa)\b', re.I)
# Normalise written numbers so "sixteen" cannot masquerade as a grounded "two".
_WORD_NUMBERS = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
    'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18,
    'nineteen': 19, 'twenty': 20, 'thirty': 30, 'forty': 40,
    'fifty': 50, 'sixty': 60, 'seventy': 70, 'eighty': 80,
    'ninety': 90, 'hundred': 100,
}
_NUMBER_RE = re.compile(r'\b\d+(?:\.\d+)?\b|\b(?:'+'|'.join(_WORD_NUMBERS)+r')\b', re.I)
_TERMS = re.compile(r'[a-z]+|\d+(?:\.\d+)?', re.I)
_STOP = set('a an and are as at be by can do does for from how in is it of on or the their these this to up what when where which who why with number maximum minimum undergraduate student may'.split())


def numbers(text: str) -> set[float]:
    """Numbers explicitly spelled out in one sentence/answer; not inferred values."""
    result = set()
    for match in _NUMBER_RE.finditer(text):
        value = match.group().lower()
        result.add(float(_WORD_NUMBERS[value]) if value in _WORD_NUMBERS else float(value))
    return result


def is_quantity_question(question: str) -> bool:
    return bool(_QUANTITY_QUESTION.search(question))


def _stem(word: str) -> str:
    word = word.lower()
    if word.endswith('ies') and len(word) > 5:
        return word[:-3] + 'y'
    if word.endswith('ing') and len(word) > 6:
        return word[:-3]
    if word.endswith('ed') and len(word) > 5:
        return word[:-2]
    if word.endswith('s') and not word.endswith('ss') and len(word) > 4:
        return word[:-1]
    if word.endswith('e') and len(word) > 5:
        return word[:-1]
    return word


# A PDF extractor can split an ordinary clause at a column/chunk boundary.
# Restore ONLY a syntactically incomplete numerical phrase across two chunks
# from the *same source and PDF page*. Never merge unrelated pages or invent
# a number: the numeric fragment must literally begin the neighboring chunk.
_JOIN_PREFIX = re.compile(r'\b(?:up to|maximum of|minimum of|at least|no more than)\s*$', re.I)
_JOIN_SUFFIX = re.compile(
    r'^\s*(?:\d+(?:\.\d+)?|\b(?:' + '|'.join(_WORD_NUMBERS) + r')\b)'
    r'\s*(?:%|percent|courses?|semesters?|weeks?|months?|years?|credits?|hours?)\b', re.I)


def _joined_quantity_passages(passages: list[Passage]) -> list[Passage]:
    """Yield evidence preserving a same-page, literal phrase split across chunks.

    This is prompt-time reconstruction, not a Chroma index rewrite. The copied
    citation metadata belongs to an original retrieved chunk on that page.
    """
    combined = []
    for before in passages:
        prefix = ' '.join(before.text.split())
        if not _JOIN_PREFIX.search(prefix):
            continue
        for after in passages:
            if (before.chunk_id == after.chunk_id or before.source != after.source
                    or before.page is None or before.page != after.page):
                continue
            suffix = ' '.join(after.text.split())
            if not _JOIN_SUFFIX.match(suffix):
                continue
            # Copy the exact opening clause, excluding unrelated later rules.
            ending = re.search(r'(?<!\d)[.!?](?!\d)(?=\s|$)', suffix)
            first_clause = suffix[:ending.end()] if ending else suffix[:140]
            joined = f'{prefix} {first_clause}'.strip()
            combined.append(Passage(chunk_id=before.chunk_id,
                                    source=before.source, section=before.section,
                                    page=before.page, score=max(before.score, after.score),
                                    text=joined))
    return combined


def best_quantitative_evidence(question: str, passages: list[Passage]) -> tuple[Passage, str, float] | None:
    """Locate a short *original quotation* that addresses the question's nouns and quantity.

    Evidence selection is generic: overlaps, quantity present, matching units, not a
    special case for summer courses. The source passage and page remain unchanged.
    """
    query_terms = {_stem(w) for w in _TERMS.findall(question)
                   if w.lower() not in _STOP and not w.isdigit()}
    if not query_terms:
        return None
    candidates = []
    repaired = _joined_quantity_passages(passages)
    for p in [*passages, *repaired]:
        text = ' '.join(p.text.split())
        # Avoid splitting decimal clause IDs such as 1.19 and amounts such as 2.00.
        sentences = re.split(r'(?<!\d)\.(?!\d)\s+(?=[A-Z0-9])|[;!?]\s+', text)
        for snippet in sentences:
            snippet = snippet.strip()
            if len(snippet) < 15 or len(snippet) > 900 or not numbers(snippet):
                continue
            terms = {_stem(w) for w in _TERMS.findall(snippet)}
            matched = len(query_terms & terms)
            coverage = matched / len(query_terms)
            # Preserve an explicit quantity unit: courses, weeks, students, percent, etc.
            count_unit_match = int(bool({'cours', 'credit', 'week', 'year', 'semest', 'percent', 'cgpa', 'gpa'} & query_terms & terms))
            # Reward a complete numerical clause reconstructed from fragments,
            # but only where its words actually match the question.
            join_bonus = .15 if p in repaired and coverage >= .5 else 0.0
            score = coverage + .12*count_unit_match + .05*p.score + join_bonus
            candidates.append((score, p, snippet))
    if not candidates:
        return None
    score, passage, snippet = max(candidates, key=lambda item: item[0])
    # A random number in a weakly related passage should never drive a response.
    if score < 0.45:
        return None
    return passage, snippet, score


def quantity_supported(question: str, answer: Answer, citations: list, passages: list[Passage]) -> bool:
    """Check explicit numeric claims against the *cited* passage, not any random passage.

    It is a conservative sanity check, NOT a substitute for factual assessment.
    A number appearing on the cited page is necessary but not sufficient evidence.
    """
    if not is_quantity_question(question) or not answer.answered_from_context:
        return True
    claimed = numbers(answer.answer)
    if not claimed:
        return False
    cited = {(c.source, c.section, c.page) for c in citations}
    source_text = ' '.join(p.text for p in passages if (p.source, p.section, p.page) in cited)
    return bool(source_text) and claimed.issubset(numbers(source_text))


# An extractive fallback is permitted only for an explicit quantity limit
# within a high-relevance original or same-page-reconstructed policy clause.
# It does not create a new fact: the answer text is a literal sentence from
# evidence, and citation metadata must match an actually retrieved passage.
_LIMIT_QUANTITY_RE = re.compile(
    r"\b(?:up\s+to|maximum\s+of|no\s+more\s+than|at\s+most)\s+"
    r"(?P<number>\d+(?:\.\d+)?|" + '|'.join(_WORD_NUMBERS) + r")\s*"
    r"(?P<unit>semesters?|courses?|weeks?|months?|years?|credits?|hours?)\b", re.I)
_UNIT_RE = re.compile(r"\bsemesters?|courses?|weeks?|months?|years?|credits?|hours?\b", re.I)


def _singular_unit(value: str) -> str:
    value = value.lower()
    return value[:-1] if value.endswith('s') else value


def grounded_extractive_quantity_answer(question: str, passages: list[Passage]) -> Answer | None:
    """Extract a directly supported numerical limit after LLM grounding fails.

    The fallback is deliberately conservative. It only acts if (a) the question
    names the same unit, (b) a highly matching retrieved clause *explicitly*
    states an upper bound, and (c) its citation metadata is backed by an
    original retrieved chunk. It never guesses, fabricates a citation or
    substitutes an unrelated number merely because the page contains one.
    """
    if not is_quantity_question(question):
        return None
    focus = best_quantitative_evidence(question, passages)
    if focus is None:
        return None
    passage, snippet, score = focus
    if score < .70:
        return None
    match = _LIMIT_QUANTITY_RE.search(snippet)
    if match is None:
        return None
    units = {_singular_unit(m.group()) for m in _UNIT_RE.finditer(question)}
    if not units or _singular_unit(match.group('unit')) not in units:
        return None
    query_terms = {_stem(w) for w in _TERMS.findall(question)
                   if w.lower() not in _STOP and not w.isdigit()}
    snippet_terms = {_stem(w) for w in _TERMS.findall(snippet)}
    # Require TWO matching topic terms in addition to the quantity unit.
    unit_terms = {'semest', 'semester', 'cours', 'course', 'week', 'month',
                  'year', 'credit', 'hour', 'many', 'number', 'normally'}
    if len((query_terms & snippet_terms) - unit_terms) < 2:
        return None
    # An authoritative, exact source/section/page tuple must have been retrieved.
    metadata=(passage.source,passage.section,passage.page)
    if not passage.page or not any((p.source,p.section,p.page)==metadata for p in passages):
        return None
    # Remove a section heading and numbered rule prefix only when present.
    # Preserve the full literal policy sentence rather than synthesize facts.
    sentence=re.sub(r'^.{0,100}?\b\d+\.\d+\s*\|\s*', '', snippet, count=1).strip()
    if len(sentence)>350 or len(sentence)<15 or not _LIMIT_QUANTITY_RE.search(sentence):
        return None
    citation=Citation(source=passage.source,section=passage.section,page=passage.page)
    answer=Answer(reasoning='Exact supporting policy sentence extracted from retrieved evidence.',
                  answer=sentence,citations=[citation],answered_from_context=True,
                  confidence='medium')
    # Check against the focus passage, including same-page literal reconstruction.
    return answer if quantity_supported(question,answer,[citation],[passage]) else None
