from app.exceptions.base import AppError, ErrorCode


class AuthenticationRequiredError(AppError):
    code = ErrorCode.AUTH_REQUIRED
    status_code = 401
    default_message = "Authentication required."


class InvalidAuthenticationError(AppError):
    code = ErrorCode.AUTH_INVALID
    status_code = 401
    default_message = "Authentication failed."


class AuthenticationForbiddenError(AppError):
    code = ErrorCode.AUTH_FORBIDDEN
    status_code = 403
    default_message = "Request verification failed."


class AuthenticationLockedError(AppError):
    code = ErrorCode.AUTH_LOCKED
    status_code = 429
    default_message = "Too many attempts. Try again later."

    def __init__(self, retry_after_seconds: int) -> None:
        retry_after = max(1, retry_after_seconds)
        super().__init__(
            headers={"Retry-After": str(retry_after)},
            details={"retry_after_seconds": retry_after},
        )


class OwnerSetupRequiredError(AppError):
    code = ErrorCode.AUTH_SETUP_REQUIRED
    status_code = 409
    default_message = "Owner setup is required."


class OwnerAlreadyConfiguredError(AppError):
    code = ErrorCode.AUTH_ALREADY_CONFIGURED
    status_code = 409
    default_message = "Owner setup is already complete."


class AuthenticationDisabledError(AppError):
    code = ErrorCode.AUTH_DISABLED
    status_code = 409
    default_message = "Protected mode is disabled."
