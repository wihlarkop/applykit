class PDFRenderError(Exception):
    pass


def html_to_pdf(html_content: str) -> bytes:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html_content)
            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
            browser.close()
            return pdf_bytes
    except ImportError as e:
        raise PDFRenderError(
            "playwright is not installed. Run: pip install playwright && playwright install chromium"
        ) from e
    except Exception as e:
        raise PDFRenderError(str(e)) from e
