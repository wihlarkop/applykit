import pytest

from app.services.scraper import _detect_ats


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://job-boards.greenhouse.io/appier/jobs/8102255", "greenhouse"),
        ("https://jobs.lever.co/acme/abc123", "lever"),
        ("https://jobs.ashbyhq.com/acme/def456", "ashby"),
        ("https://acme.applytojob.com/apply/xyz789", "jazzhr"),
        ("https://acme.bamboohr.com/careers/12", "generic"),
        ("https://acme.wd1.myworkdayjobs.com/careers/job/456", "generic"),
    ],
)
def test_detect_ats(url: str, expected: str) -> None:
    assert _detect_ats(url) == expected
