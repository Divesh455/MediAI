from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.frontend import router as frontend_router
from .api.routes import router
from .core.config import APP_TITLE, FRONTEND_DIR, PROFILE_IMAGES_DIR, UPLOADS_DIR
from .db import init_db


def create_app() -> FastAPI:
    init_db()
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    app = FastAPI(title=APP_TITLE)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
    app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
    app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
    app.include_router(frontend_router)
    return app


app = create_app()
