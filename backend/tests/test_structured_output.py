import pytest
from pydantic import BaseModel

from app.exceptions.llm import LLMOutputError
from app.services.llm import parse_structured_output


class ExampleOutput(BaseModel):
    answer: str
    score: int


def test_parses_raw_json_into_requested_schema():
    """Structured output returns the requested Pydantic model."""
    result = parse_structured_output(
        '{"answer":"ok","score":95}',
        ExampleOutput,
    )

    assert result == ExampleOutput(answer="ok", score=95)


def test_parses_one_markdown_json_fence():
    result = parse_structured_output(
        '```json\n{"answer":"ok","score":95}\n```',
        ExampleOutput,
    )

    assert result.score == 95


@pytest.mark.parametrize(
    "raw",
    [
        'Here is the result: {"answer":"ok","score":95}',
        '{"answer":"ok","score":95} trailing text',
        '{"answer":"ok"}',
        'not json',
    ],
)
def test_rejects_prose_malformed_json_and_schema_mismatch(raw):
    with pytest.raises(LLMOutputError) as exc_info:
        parse_structured_output(raw, ExampleOutput)

    assert exc_info.value.message == (
        "The AI provider returned an invalid structured response. Please try again."
    )
    assert raw not in exc_info.value.message
