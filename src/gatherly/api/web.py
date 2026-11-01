"""Serve the small browser interface from a fixed asset allowlist."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

WEB_ROOT = Path(__file__).resolve().parents[1] / "web"
ASSETS = {"app.js", "render.js", "model.js", "style.css", "mark.svg"}
WEB_CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; "
    "img-src 'self'; connect-src 'self'; font-src 'self'; "
    "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
)
router = APIRouter(include_in_schema=False)


@router.get("/")
async def planner_page() -> FileResponse:
    """Return the planner with a restrictive same-origin content policy."""
    return FileResponse(
        WEB_ROOT / "index.html",
        headers={"Content-Security-Policy": WEB_CSP, "Cache-Control": "no-store"},
    )


@router.get("/assets/{name}")
async def planner_asset(name: str) -> FileResponse:
    """Serve public assets only, with bounded caching and traversal protection."""
    if name not in ASSETS:
        raise HTTPException(status_code=404)
    return FileResponse(
        WEB_ROOT / name, headers={"Cache-Control": "public, max-age=3600"}
    )
