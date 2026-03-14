import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from alembic.config import Config as AlembicConfig
from alembic import command as alembic_command

from app.routes import profile, generate, import_cv


def run_migrations() -> None:
    alembic_cfg = AlembicConfig(
        os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
    )
    alembic_command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    yield


app = FastAPI(title="ApplyKit API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc.detail)})


app.include_router(profile.router, prefix="/api")
app.include_router(generate.router, prefix="/api")
app.include_router(import_cv.router, prefix="/api")
