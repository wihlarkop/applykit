import pytest

from app.resume_readiness.extraction import PdfLimitExceeded, extract_pdf
from integration.pdf import html_to_pdf


def test_extracts_text_and_page_count():
    pdf_bytes = html_to_pdf(
        "<html><body><h1>Edo Example</h1><p>Backend Engineer</p></body></html>"
    )

    result = extract_pdf(pdf_bytes)

    assert result.page_count == 1
    assert "Backend Engineer" in result.text
    assert result.has_text_layer is True


def test_rejects_pdf_above_page_limit():
    pages = "".join(
        f'<section style="page-break-after: always">Page {index}</section>'
        for index in range(11)
    )
    pdf_bytes = html_to_pdf(f"<html><body>{pages}</body></html>")

    with pytest.raises(PdfLimitExceeded):
        extract_pdf(pdf_bytes)


def test_empty_page_has_no_text_layer():
    pdf_bytes = html_to_pdf("<html><body></body></html>")

    result = extract_pdf(pdf_bytes)

    assert result.has_text_layer is False
    assert result.warnings == ("page_1_has_no_text",)
