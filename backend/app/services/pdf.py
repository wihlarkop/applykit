import html
import re


class PDFRenderError(Exception):
    pass


def _strip_html(raw: str) -> str:
    text = re.sub(r'<[^>]+>', '', raw)
    return html.unescape(text).strip()


# Normalize Unicode typography to ASCII equivalents so Helvetica can render them
_UNICODE_MAP = str.maketrans({
    '\u2013': '-',    # en-dash
    '\u2014': '-',    # em-dash
    '\u2018': "'",    # left single quote
    '\u2019': "'",    # right single quote
    '\u201c': '"',    # left double quote
    '\u201d': '"',    # right double quote
    '\u2026': '...',  # ellipsis
    '\u00a0': ' ',    # non-breaking space
    '\u2022': '-',    # bullet
    '\u2010': '-',    # hyphen
    '\u2011': '-',    # non-breaking hyphen
    '\u2012': '-',    # figure dash
    '\u2015': '-',    # horizontal bar
    '\u2192': '->',   # right arrow
    '\u2190': '<-',   # left arrow
    '\u00b7': '.',    # middle dot
})


def _normalize(text: str) -> str:
    text = text.translate(_UNICODE_MAP)
    # Replace any remaining non-Latin-1 characters with '?'
    return text.encode('latin-1', errors='replace').decode('latin-1')


def html_to_pdf(html_content: str) -> bytes:
    try:
        from fpdf import FPDF

        text = _normalize(_strip_html(html_content))

        pdf = FPDF()
        pdf.set_margins(25, 25, 25)
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=25)
        pdf.set_font('Helvetica', size=11)

        for line in text.split('\n'):
            if line.strip():
                pdf.multi_cell(0, 6, line)
            else:
                pdf.ln(4)

        return bytes(pdf.output())
    except ImportError as e:
        raise PDFRenderError("fpdf2 is not installed. Run: uv add fpdf2") from e
    except Exception as e:
        raise PDFRenderError(str(e)) from e
