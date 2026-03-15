class PDFRenderError(Exception):
    pass


def html_to_pdf(html: str) -> bytes:
    try:
        from weasyprint import (
            HTML,  # lazy import — only fails if GTK missing AND PDF is requested
        )

        return HTML(string=html).write_pdf()
    except ImportError as e:
        raise PDFRenderError(
            "WeasyPrint requires GTK. See README for Windows setup instructions."
        ) from e
    except Exception as e:
        raise PDFRenderError(str(e)) from e
