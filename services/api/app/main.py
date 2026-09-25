from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import api_router
from app.config import get_settings
from app.db.session import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="AI Nutrition Assistant API",
        version="0.1.0",
        description="Milestone 1 prototype backend",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        message_related = any("message" in err.get("loc", ()) for err in errors)
        first = errors[0] if errors else {}
        err_type = str(first.get("type", ""))
        msg = str(first.get("msg", "Invalid request"))

        if message_related and (
            "blank" in msg.lower()
            or "empty" in msg.lower()
            or "whitespace" in msg.lower()
            or err_type in {"missing", "string_too_short"}
        ):
            code = "empty_message"
        elif message_related and (
            "max_length" in err_type or "too_long" in err_type or "at most" in msg.lower()
        ):
            code = "message_too_long"
        elif message_related:
            code = "validation_error"
        else:
            code = "validation_error"

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": code, "message": msg}},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        _request: Request, exc: HTTPException
    ) -> JSONResponse:
        if isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
            return JSONResponse(
                status_code=exc.status_code,
                content={"error": exc.detail},
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": "http_error",
                    "message": str(exc.detail),
                }
            },
        )

    @app.get("/")
    def root() -> dict[str, str]:
        """Avoid a bare 404 on the Railway public URL (UI is on Vercel)."""
        return {
            "service": "AI Nutrition Assistant API",
            "health": "/health",
            "chat": "POST /api/chat",
            "note": "Open the Vercel frontend URL in your browser; this host is the API only.",
        }

    app.include_router(api_router)
    return app


app = create_app()
