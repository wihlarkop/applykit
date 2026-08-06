from app.exceptions import (
    RoleMatchAnalysisNotFoundError,
    RoleMatchProfileRequiredError,
)


def test_role_match_analysis_not_found_error_is_stable() -> None:
    error = RoleMatchAnalysisNotFoundError(42)
    assert error.status_code == 404
    assert error.to_envelope().model_dump(mode="json") == {
        "error": {
            "code": "ROLE_MATCH_ANALYSIS_NOT_FOUND",
            "message": "Role match analysis was not found.",
            "details": {"analysis_id": 42},
        }
    }


def test_role_match_profile_required_error_is_a_conflict() -> None:
    error = RoleMatchProfileRequiredError()
    assert error.status_code == 409
    assert error.to_envelope().model_dump(mode="json") == {
        "error": {
            "code": "ROLE_MATCH_PROFILE_REQUIRED",
            "message": "A profile is required to re-analyze this role match.",
            "details": {},
        }
    }
