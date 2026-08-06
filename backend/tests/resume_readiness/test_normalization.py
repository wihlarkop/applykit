from app.resume_readiness.normalization import normalize_text


def test_normalize_text_handles_bullets_urls_and_whitespace():
    raw = "Built APIs • FastAPI\nhttps://example.com  "
    assert normalize_text(raw) == "built apis fastapi https example com"


def test_normalize_text_handles_email_consistently():
    assert normalize_text("Edo@Example.com") == "edo at example com"
