from app.exceptions.base import AppError, ErrorCode


class RoleMatchAnalysisNotFoundError(AppError):
    code = ErrorCode.ROLE_MATCH_ANALYSIS_NOT_FOUND
    status_code = 404
    default_message = "Role match analysis was not found."

    def __init__(self, analysis_id: int) -> None:
        super().__init__(details={"analysis_id": analysis_id})


class RoleMatchProfileRequiredError(AppError):
    code = ErrorCode.ROLE_MATCH_PROFILE_REQUIRED
    status_code = 409
    default_message = "A profile is required to re-analyze this role match."
