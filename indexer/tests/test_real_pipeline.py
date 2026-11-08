from __future__ import annotations
from pathlib import Path
import pytest
from pipeline.extract import extract
from pipeline.clean import clean
from pipeline.chunk import chunk

FIXTURES=Path(__file__).resolve().parents[2]/'eval'/'fixtures'

def test_markdown_frontmatter_is_removed():
    doc=extract(str(FIXTURES/'academic-rules-2026.md'),'2026',False)
    assert 'doc_version:' not in doc.pages[0].text
    assert '80 percent' in doc.pages[0].text

def test_chunking_preserves_exact_terms_and_versions():
    doc=clean(extract(str(FIXTURES/'academic-rules-2026.md'),'2026',False))
    chunks=chunk(doc,50,10)
    assert chunks
    assert any('2.00' in c.text for c in chunks)
    assert any('80 percent' in c.text for c in chunks)
    assert all(c.doc_version=='2026' and not c.superseded for c in chunks)
    assert all(c.page==1 and c.source=='academic-rules-2026.md' for c in chunks)
    assert len({c.id for c in chunks})==len(chunks)

def test_older_version_is_marked_superseded():
    doc=clean(extract(str(FIXTURES/'academic-rules-2023.md'),'2023',True))
    pieces=chunk(doc,100,20)
    assert any('75 percent' in c.text for c in pieces)
    assert all(c.superseded for c in pieces)

def test_invalid_overlap_is_rejected():
    doc=extract(str(FIXTURES/'fees-2026.md'),'2026',False)
    with pytest.raises(ValueError): chunk(doc,100,100)

def test_html_parser_keeps_table_cells(tmp_path):
    source=tmp_path/'table.html'
    source.write_text('<html><body><table><tr><th>Fee</th><th>PKR</th></tr><tr><td>BS</td><td>10000</td></tr></table><script>IGNORE</script></body></html>')
    doc=extract(str(source),'2026',False)
    assert '10000' in doc.pages[0].text
    assert 'IGNORE' not in doc.pages[0].text
