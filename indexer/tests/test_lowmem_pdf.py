"""Smoke tests for Poppler + per-page OCR path (system tools required)."""
from pathlib import Path
import pytest
from pipeline.extract import extract


def test_pdf_pages_tables_and_ocr(tmp_path):
    reportlab = pytest.importorskip('reportlab.pdfgen.canvas')
    path = tmp_path / 'mixed.pdf'
    c = reportlab.Canvas(str(path), pagesize=(612, 792))
    c.drawString(72, 700, 'Academic policy for all undergraduate students')
    c.drawString(72, 670, 'Grade          Points')
    c.drawString(72, 650, 'A              4.00')
    c.showPage()
    # Force image OCR: embed text inside a raster PNG rather than the PDF text layer.
    PIL = pytest.importorskip('PIL.Image')
    draw_mod = pytest.importorskip('PIL.ImageDraw')
    img = PIL.new('RGB', (900, 190), 'white')
    draw = draw_mod.Draw(img)
    draw.text((30, 60), 'SCANNED UNIVERSITY DOCUMENT', fill='black')
    pic = tmp_path / 'scan.png'
    img.save(pic)
    c.drawImage(str(pic), 30, 500, width=500, height=150)
    c.save()
    progress = []
    doc = extract(str(path), '2026-06', False,
                  progress=lambda n,total,ocr: progress.append((n,total,ocr)))
    assert len(doc.pages) == 2
    assert 'Academic policy' in doc.pages[0].text
    assert '4.00' in doc.pages[0].text
    assert doc.pages[0].ocr is False
    assert doc.pages[1].ocr is True
    assert progress == [(1,2,False),(2,2,True)]
    assert doc.pages[1].source == 'mixed.pdf'
    assert doc.pages[1].page == 2


def test_non_pdf_html_still_extracts(tmp_path):
    p = tmp_path / 'fees.html'
    p.write_text('<table><tr><td>Fee</td><td>1000</td></tr></table><script>IGNORE</script>')
    doc = extract(str(p), '2026', False)
    assert 'Fee | 1000' in doc.pages[0].text
    assert 'IGNORE' not in doc.pages[0].text
