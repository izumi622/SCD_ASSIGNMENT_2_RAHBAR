"""Structure-aware chunking; prefer headings and paragraphs over hard splits."""
from __future__ import annotations
import hashlib
import re
from .models import Chunk, Document

_HEADING = re.compile(r'^(?:#{1,6}\s+.+|(?:\d+(?:\.\d+)*[.)]?\s+)[A-Za-z].{3,}|[A-Z][A-Z\s]{8,})$')


def _words(text: str) -> list[str]:
    return text.split()


def chunk(doc: Document, size: int, overlap: int) -> list[Chunk]:
    if size < 10 or overlap < 0 or overlap >= size:
        raise ValueError('chunk size must be >=10 and 0 <= overlap < size')
    out: list[Chunk] = []
    for page in doc.pages:
        if not page.text.strip(): continue
        section = 'Unheaded section'
        para_blocks = re.split(r'\n\s*\n', page.text)
        segments: list[tuple[str,str]] = []
        for block in para_blocks:
            for line in block.splitlines():
                stripped = line.strip()
                if stripped and _HEADING.match(stripped) and len(stripped.split()) <= 20:
                    section = stripped.lstrip('# ').strip()
                    # Keep the heading in the evidence too: citation text should not lose clauses.
                if stripped:
                    segments.append((section, stripped))
        if not segments: continue
        current: list[str] = []
        prev_section = segments[0][0]
        def emit():
            if not current: return
            content = ' '.join(current).strip()
            pos = len(out)
            seed = f'{doc.source}|{doc.doc_version}|{page.page}|{pos}|{content}'.encode()
            out.append(Chunk(id=hashlib.sha256(seed).hexdigest()[:24], text=content,
                             source=doc.source, section=prev_section, page=page.page,
                             doc_version=doc.doc_version, superseded=doc.superseded))
        for sec, raw in segments:
            parts = _words(raw)
            if sec != prev_section:
                emit(); current=[]; prev_section=sec
            while parts:
                room = size-len(current)
                if room <= 0:
                    emit(); current=current[-overlap:] if overlap else []; room=size-len(current)
                take = parts[:room]; parts = parts[room:]
                current.extend(take)
                if parts:
                    emit(); current=current[-overlap:] if overlap else []
        emit()
    return out
