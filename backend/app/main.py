"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.eval import router as eval_router
from app.api.routes.system import router as system_router
from app.api.routes.tasks import router as tasks_router
from app.core.bootstrap import ensure_database_schema, ensure_runtime_directories
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_runtime_directories()
    ensure_database_schema()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="碰撞预警 Data Agent",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(tasks_router)
    app.include_router(system_router)
    app.include_router(eval_router)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    @app.get("/")
    def root() -> dict[str, str]:
        return {"service": "collision-agent", "docs": "/docs"}

    return app


app = create_app()
