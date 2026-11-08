"""Memory-bounded PDF/HTML/Markdown extraction with page provenance.

Poppler and Tesseract run as short-lived subprocesses, not as large PDF/page
objects held inside Python. Each scanned page is rasterised separately with a
bounded longest edge and OCR'd through Tesseract's CLI.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable

from .models import Document, Page


class TextHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self.hidden += 1
        if tag in ('p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr', 'section'):
            self.parts.append('\n')
        if tag in ('td', 'th'):
            self.parts.append(' | ')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'):
            self.hidden = max(self.hidden - 1, 0)
        if tag in ('p', 'div', 'tr', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def _run(args: list[str], *, timeout: int = 180, env: dict[str, str] | None = None) -> str:
    """Run one Poppler/Tesseract process; fail with an actionable error."""
    try:
        result = subprocess.run(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            encoding='utf-8', errors='replace', timeout=timeout, env=env,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f'{args[0]} timed out after {timeout}s') from exc
    if result.returncode != 0:
        raise RuntimeError(f'{args[0]} exited {result.returncode}: {result.stderr[-1000:]}')
    return result.stdout


def _num_pages(pdf: Path) -> int:
    info = _run(['pdfinfo', str(pdf)], timeout=90)
    match = re.search(r'^Pages:\s*(\d+)\s*$', info, flags=re.MULTILINE)
    if not match or int(match.group(1)) < 1:
        raise RuntimeError(f'Cannot determine PDF page count: {pdf.name}')
    return int(match.group(1))


def _keep_table_columns(text: str) -> str:
    """Make layout-spaced columns explicit before the cleaner collapses spaces.

    This preserves the *reading order* of tabular rows. It is not a guarantee
    of reliable table-cell detection in arbitrary multi-column PDFs.
    """
    return '\n'.join(re.sub(r'(?<=\S)[ \t]{3,}(?=\S)', ' | ', line)
                     for line in text.splitlines())


def _ocr_pdf_page(pdf: Path, ix: int, temp: Path) -> str:
    prefix = temp / 'page'
    # Rasterise at bounded dimensions: a scan/poster cannot create a huge PIL
    # object or force Tesseract to process a 5K+ pixel image in memory.
    _run([
        'pdftoppm', '-f', str(ix), '-l', str(ix), '-scale-to', '1800',
        '-gray', '-jpeg', '-singlefile', str(pdf), str(prefix),
    ], timeout=180)
    jpg = prefix.with_suffix('.jpg')
    if not jpg.exists():
        raise RuntimeError(f'pdftoppm did not create image for {pdf.name} page {ix}')
    try:
        # Keep the OCR process memory bounded and prevent many OpenMP workers.
        env = dict(os.environ, OMP_THREAD_LIMIT='1')
        return _run(['tesseract', str(jpg), 'stdout', '--psm', '3'], timeout=180, env=env)
    finally:
        jpg.unlink(missing_ok=True)


def extract(
    path: str, doc_version: str, superseded: bool,
    progress: Callable[[int, int, bool], None] | None = None,
) -> Document:
    target = Path(path)
    doc = Document(source=target.name, doc_version=str(doc_version), superseded=superseded)
    ext = target.suffix.lower()
    if ext == '.pdf':
        count = _num_pages(target)
        with tempfile.TemporaryDirectory(prefix='rahbar-extract-') as directory:
            temp = Path(directory)
            textfile = temp / 'pages.txt'
            # Poppler writes all page text to disk (not a persistent Python PDF
            # object). Form-feed separators retain the source page numbers.
            _run(['pdftotext', '-layout', '-enc', 'UTF-8', str(target), str(textfile)], timeout=300)
            raw_pages = textfile.read_text(encoding='utf-8', errors='replace').split('\f')
            # Poppler generally emits one trailing form feed.
            if len(raw_pages) > count and not ''.join(raw_pages[count:]).strip():
                raw_pages = raw_pages[:count]
            if len(raw_pages) != count:
                raise RuntimeError(
                    f'PDF page alignment failed for {target.name}: '
                    f'pdfinfo={count}, pdftotext={len(raw_pages)}'
                )
            for ix, body in enumerate(raw_pages, 1):
                ocr = len(body.strip()) < 20
                if ocr:
                    body = _ocr_pdf_page(target, ix, temp)
                doc.pages.append(Page(source=target.name, page=ix,
                                      text=_keep_table_columns(body), ocr=ocr))
                if progress is not None:
                    progress(ix, count, ocr)
    elif ext in ('.md', '.txt', '.html', '.htm'):
        data = target.read_text(encoding='utf-8-sig', errors='replace')
        if ext == '.md':
            data = re.sub(r'\A---\s*\n.*?\n---\s*\n', '', data, count=1, flags=re.S)
        if ext in ('.html', '.htm'):
            parser = TextHTML()
            parser.feed(data)
            data = ''.join(parser.parts)
        doc.pages.append(Page(source=target.name, page=1, text=data))
    else:
        raise ValueError(f'unsupported document type: {target}')
    return doc
