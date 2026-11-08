"""Clean text conservatively without stripping clauses and headings."""
from __future__ import annotations
import re
from collections import Counter
from .models import Document


def clean(doc: Document) -> Document:
    # Only remove lines recurring at the *first or last* edge of >=3 pages.
    edge_counts = Counter()
    for page in doc.pages:
        lines = [s.strip() for s in page.text.splitlines() if s.strip()]
        edge_counts.update(set(lines[:1] + lines[-1:]))
    repeating = {line for line, count in edge_counts.items()
                 if len(doc.pages) >= 3 and count >= max(3, (len(doc.pages)+1)//2)
                 and len(line) < 100}
    for page in doc.pages:
        lines = page.text.replace('\r', '').splitlines()
        if lines and lines[0].strip() in repeating: lines.pop(0)
        if lines and lines[-1].strip() in repeating: lines.pop()
        text = '\n'.join(lines)
        text = re.sub(r'(?<=\w)-\n(?=\w)', '', text)  # hyphenated line-wrap
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        page.text = text.strip()
    return doc
