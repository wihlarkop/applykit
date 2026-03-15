import io

MIN_TEXT_LENGTH = 100


def extract_text(
    file_content: bytes | None = None,
    filename: str | None = None,
    text: str | None = None,
) -> str:
    """Extract raw text from a PDF, DOCX, or plain text input."""
    if file_content is not None and filename is not None:
        ext = filename.lower().rsplit(".", 1)[-1]
        if ext == "pdf":
            return _extract_pdf(file_content)
        elif ext == "docx":
            return _extract_docx(file_content)
        else:
            raise ValueError(f"Unsupported file type: .{ext}")
    elif text is not None:
        return text.strip()
    else:
        raise ValueError("Provide either file_content+filename or text.")


def _extract_pdf(content: bytes) -> str:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return "\n".join(pages).strip()


def _extract_docx(content: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(content))
    return "\n".join(para.text for para in doc.paragraphs).strip()


def validate_extracted_text(text: str) -> None:
    if len(text) < MIN_TEXT_LENGTH:
        raise ValueError(
            f"Extracted text too short ({len(text)} chars). "
            "File may be empty, scanned, or unreadable."
        )
