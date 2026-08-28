from weasyprint import HTML
from weasyprint.document import Document


class PDFRenderError(Exception):
    pass


def html_to_document(html_content: str) -> Document:
    # Skips PDF encoding; cheaper than html_to_pdf() when only page count is needed.
    try:
        return HTML(string=html_content).render()
    except ImportError as e:
        raise PDFRenderError(
            "weasyprint is not installed. Run: pip install weasyprint"
        ) from e
    except Exception as e:
        raise PDFRenderError(str(e)) from e


def document_to_pdf(document: Document) -> bytes:
    try:
        return document.write_pdf()
    except Exception as e:
        raise PDFRenderError(str(e)) from e


def html_to_pdf(html_content: str) -> bytes:
    return document_to_pdf(html_to_document(html_content))
