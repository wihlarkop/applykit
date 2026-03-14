from weasyprint import HTML


class PDFRenderError(Exception):
    pass


def html_to_pdf(html: str) -> bytes:
    try:
        return HTML(string=html).write_pdf()
    except Exception as e:
        raise PDFRenderError(str(e)) from e
