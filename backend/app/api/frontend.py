from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.app.core.config import FRONTEND_DIR


router = APIRouter()

PAGE_FILES = {
    "dashboard": "dashboard.html",
    "predict": "predict.html",
    "xray": "xray.html",
    "chatbot": "chatbot.html",
    "reports": "reports.html",
    "history": "history.html",
    "profile": "profile.html",
    "settings": "settings.html",
    "login": "login.html",
    "register": "register.html",
}

ASSET_EXTENSIONS = {
    ".ico",
    ".jpg",
    ".jpeg",
    ".png",
    ".svg",
    ".webp",
}


def html_response(filename: str) -> FileResponse:
    path = FRONTEND_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Page not found: {filename}")
    return FileResponse(path)


@router.get("/", include_in_schema=False)
def index() -> FileResponse:
    return html_response("index.html")


@router.get("/{page_name}", include_in_schema=False)
def page(page_name: str) -> FileResponse:
    if page_name in PAGE_FILES:
        return html_response(PAGE_FILES[page_name])

    asset_path = FRONTEND_DIR / page_name
    if asset_path.suffix.lower() in ASSET_EXTENSIONS and asset_path.exists():
        return FileResponse(asset_path)

    raise HTTPException(status_code=404, detail="Page not found")


@router.get("/{page_name}.html", include_in_schema=False)
def legacy_page(page_name: str) -> FileResponse:
    if page_name == "index":
        return html_response("index.html")
    if page_name in PAGE_FILES:
        return html_response(PAGE_FILES[page_name])
    raise HTTPException(status_code=404, detail="Page not found")
