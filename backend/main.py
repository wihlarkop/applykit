from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.exceptions import (
    BaseCustomException,
    error_response,
)
from app.routes import (
    analyze,
    applications,
    generate,
    history,
    import_cv,
    profile,
    profiles,
    scrape,
    settings,
    usage,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code, content={"detail": str(exc.detail)}
    )


async def base_custom_exception_handler(
    request: Request, exc: BaseCustomException
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            message=exc.message,
            status_code=exc.status_code,
            error_code=exc.error_code,
            details=exc.details,
        ),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response(
            message="Validation error",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details={"errors": errors},
        ),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    message = getattr(exc, "message", None) or getattr(exc, "msg", None) or str(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            message=message or "An unexpected error occurred",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_SERVER_ERROR",
        ),
    )


exception_handlers = {
    HTTPException: http_exception_handler,
    BaseCustomException: base_custom_exception_handler,
    RequestValidationError: validation_exception_handler,
    Exception: generic_exception_handler,
}


app = FastAPI(
    title="ApplyKit API",
    lifespan=lifespan,
    exception_handlers=exception_handlers,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(applications.router, prefix="/api")
app.include_router(profile.router, prefix="/api")
app.include_router(profiles.router, prefix="/api")
app.include_router(generate.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(import_cv.router, prefix="/api")
app.include_router(scrape.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(usage.router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
