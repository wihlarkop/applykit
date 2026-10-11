import io

import pdfplumber
import pytest

from integration.pdf import html_to_pdf
from integration.template import render_cv_template, safe_project_url


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://example.com/project", "https://example.com/project"),
        ("http://example.com", "http://example.com"),
        ("example.com/project", "https://example.com/project"),
        ("//example.com/project", "https://example.com/project"),
        ("javascript:alert(1)", None),
        ("file:///C:/review-only-nonexistent.txt", None),
        ("data:text/html,test", None),
        ("java\nscript:alert(1)", None),
        (" https://example.com", None),
        ("https://", None),
        ("https://[", None),
    ],
)
def test_project_url_allows_only_web_links(url, expected):
    assert safe_project_url(url) == expected


@pytest.mark.parametrize(
    "url, expected",
    [
        ("javascript:alert(1)", []),
        ("file:///C:/review-only-nonexistent.txt", []),
        ("example.com/project", ["https://example.com/project"]),
    ],
)
def test_rendered_pdf_has_only_safe_project_annotations(url, expected):
    html = render_cv_template(
        {
            "name": "Jane",
            "email": "j@example.com",
            "projects": [
                {
                    "name": "Visible Project",
                    "description": "Real work",
                    "tech_stack": [],
                    "link": url,
                }
            ],
        }
    )
    with pdfplumber.open(io.BytesIO(html_to_pdf(html))) as pdf:
        uris = [
            annotation["uri"]
            for page in pdf.pages
            for annotation in page.annots or []
            if annotation.get("uri")
        ]
        assert uris == expected
        assert "Visible Project" in pdf.pages[0].extract_text()
