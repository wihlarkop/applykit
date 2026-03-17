from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes import generate, history, import_cv, profile, profiles, scrape, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    return JSONResponse(
        status_code=exc.status_code, content={"detail": str(exc.detail)}
    )


app.include_router(profile.router, prefix="/api")
app.include_router(profiles.router, prefix="/api")
app.include_router(generate.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(import_cv.router, prefix="/api")
app.include_router(scrape.router, prefix="/api")
app.include_router(settings.router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
