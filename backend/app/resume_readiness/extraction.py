from __future__ import annotations

from io import BytesIO

import pdfplumber

from app.resume_readiness.constants import (
    EXTRACTED_TEXT_MAX_CHARS,
    PDF_MAX_BYTES,
    PDF_MAX_PAGES,
)
from app.resume_readiness.domain import ExtractedDocument, ExtractedPage


class PdfLimitExceeded(ValueError):
    pass


class PdfExtractionFailed(RuntimeError):
    pass


def extract_pdf(pdf_bytes: bytes) -> ExtractedDocument:
    if len(pdf_bytes) > PDF_MAX_BYTES:
        raise PdfLimitExceeded(
            f"PDF exceeds the {PDF_MAX_BYTES // (1024 * 1024)} MB analysis limit."
        )

    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            page_count = len(pdf.pages)
            if page_count > PDF_MAX_PAGES:
                raise PdfLimitExceeded(
                    f"PDF has {page_count} pages; the limit is {PDF_MAX_PAGES}."
                )

            extracted_pages: list[ExtractedPage] = []
            warnings: list[str] = []
            total_chars = 0

            for page_number, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                total_chars += len(text)
                if total_chars > EXTRACTED_TEXT_MAX_CHARS:
                    raise PdfLimitExceeded(
                        "Extracted text exceeds the analysis character limit."
                    )
                if not text.strip():
                    warnings.append(f"page_{page_number}_has_no_text")
                extracted_pages.append(
                    ExtractedPage(
                        page_number=page_number,
                        text=text,
                        width=float(page.width) if page.width is not None else None,
                        height=float(page.height) if page.height is not None else None,
                    )
                )
    except PdfLimitExceeded:
        raise
    except Exception as exc:
        raise PdfExtractionFailed("Could not parse the generated resume PDF.") from exc

    combined_text = "\n\n".join(page.text for page in extracted_pages).strip()
    return ExtractedDocument(
        text=combined_text,
        pages=tuple(extracted_pages),
        page_count=page_count,
        has_text_layer=bool(combined_text),
        warnings=tuple(warnings),
    )
