from app.services import parse_job_description


def test_full_job_description_reaches_the_llm_past_the_old_truncation_point(monkeypatch):
    """Salary/EEO statements are commonly appended at the end of a posting -
    the parser must not silently drop content past any arbitrary cutoff."""
    captured = {}

    def fake_call_llm(prompt: str, **kwargs):
        captured["prompt"] = prompt
        return '{"company_name": null, "role_title": null, "location": null, "salary": "$100,000-$150,000"}'

    monkeypatch.setattr(parse_job_description, "call_llm", fake_call_llm)

    padding = "Responsibility filler text. " * 200  # well past 4000 chars
    marker = "SALARY_RANGE_MARKER: $100,000-$150,000"
    long_description = f"{padding}{marker}"
    assert len(long_description) > 4000

    parse_job_description.parse_job_description(
        long_description,
        "openai/gpt-4.1-mini",
        "test-key",
    )

    assert marker in captured["prompt"]
