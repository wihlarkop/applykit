from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.middleware import AuthMiddleware
from app.auth.startup import initialize_auth
from app.config import get_settings
from app.exceptions.handlers import exception_handlers
from app.http_client import start_http_client, stop_http_client
from app.routes import (
    analyze,
    applications,
    auth,
    generate,
    history,
    import_cv,
    profile,
    profiles,
    readiness,
    resume_readiness,
    role_match_generate,
    scrape,
    settings,
    usage,
)
from app.security.deployment import manual_bind_host, validate_deployment_security
from app.services.credential_vault_startup import initialize_credential_vault
from app.services.usage_logging import stop_usage_logger

_settings = get_settings()
validate_deployment_security(_settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_credential_vault(_settings)
    initialize_auth(_settings)
    await start_http_client()
    try:
        yield
    finally:
        stop_usage_logger()
        await stop_http_client()


app = FastAPI(
    title=_settings.app_title,
    lifespan=lifespan,
    exception_handlers=exception_handlers,
    docs_url="/docs" if _settings.debug else None,
    redoc_url="/redoc" if _settings.debug else None,
    openapi_url="/openapi.json" if _settings.debug else None,
)

app.add_middleware(AuthMiddleware, settings=_settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api")
app.include_router(applications.router, prefix="/api")
app.include_router(profile.router, prefix="/api")
app.include_router(profiles.router, prefix="/api")
app.include_router(readiness.router, prefix="/api", tags=["readiness"])
app.include_router(generate.router, prefix="/api")
app.include_router(role_match_generate.router, prefix="/api")
app.include_router(resume_readiness.router, prefix="/api", tags=["resume-readiness"])
app.include_router(analyze.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(import_cv.router, prefix="/api")
app.include_router(scrape.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(usage.router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=manual_bind_host(_settings),
        port=8000,
        reload=True,
    )
