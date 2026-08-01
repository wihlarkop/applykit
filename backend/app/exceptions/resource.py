from app.exceptions.base import AppError, ErrorCode


class NotFoundError(AppError):
    code = ErrorCode.RESOURCE_NOT_FOUND
    status_code = 404
    default_message = "Resource was not found."

    def __init__(self, resource: str, identifier: str | int) -> None:
        super().__init__(
            f"{resource} with identifier '{identifier}' not found",
            details={"resource": resource, "identifier": identifier},
        )


class ConflictError(AppError):
    code = ErrorCode.RESOURCE_CONFLICT
    status_code = 409
    default_message = "Resource state conflicts with the request."

    def __init__(
        self,
        resource: str,
        identifier: str | int,
        message: str | None = None,
    ) -> None:
        super().__init__(
            message or f"{resource} with identifier '{identifier}' already exists",
            details={"resource": resource, "identifier": identifier},
        )
