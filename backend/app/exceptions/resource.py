from app.exceptions.base import AppError, ErrorCode


class ProfileNotFoundError(AppError):
    code = ErrorCode.PROFILE_NOT_FOUND
    status_code = 404
    default_message = "Profile was not found."

    def __init__(self, profile_id: int) -> None:
        super().__init__(details={"profile_id": profile_id})


class ApplicationNotFoundError(AppError):
    code = ErrorCode.APPLICATION_NOT_FOUND
    status_code = 404
    default_message = "Application was not found."

    def __init__(self, application_id: int) -> None:
        super().__init__(details={"application_id": application_id})


class HistoryEntryNotFoundError(AppError):
    code = ErrorCode.HISTORY_ENTRY_NOT_FOUND
    status_code = 404
    default_message = "History entry was not found."

    def __init__(self, resource: str, entry_id: int) -> None:
        super().__init__(
            f"{resource} was not found.",
            details={"resource": resource, "entry_id": entry_id},
        )


class ProviderNotFoundError(AppError):
    code = ErrorCode.PROVIDER_NOT_FOUND
    status_code = 404
    default_message = "Provider was not found."

    def __init__(self, provider_id: str) -> None:
        super().__init__(details={"provider_id": provider_id})


class GeneratedCVNotFoundError(AppError):
    code = ErrorCode.GENERATED_CV_NOT_FOUND
    status_code = 404
    default_message = "Generated resume was not found."

    def __init__(self, generated_cv_id: int) -> None:
        super().__init__(details={"generated_cv_id": generated_cv_id})


class ResumeReadinessAnalysisNotFoundError(AppError):
    code = ErrorCode.RESUME_READINESS_ANALYSIS_NOT_FOUND
    status_code = 404
    default_message = "Resume Readiness analysis was not found."

    def __init__(
        self,
        analysis_id: int | None = None,
        *,
        message: str | None = None,
    ) -> None:
        details = {"analysis_id": analysis_id} if analysis_id is not None else {}
        super().__init__(message, details=details)
