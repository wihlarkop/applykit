from weasyprint import HTML


class PDFRenderError(Exception):
    pass


def html_to_pdf(html_content: str) -> bytes:
    try:
        return HTML(string=html_content).write_pdf()
    except ImportError as e:
        raise PDFRenderError(
            "weasyprint is not installed. Run: pip install weasyprint"
        ) from e
    except Exception as e:
        raise PDFRenderError(str(e)) from e
