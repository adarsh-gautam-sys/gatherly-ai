"""Development-only Swagger UI with a hash-authorized bootstrap script."""

import base64
import hashlib
import re

from fastapi import APIRouter
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.responses import HTMLResponse, RedirectResponse

router = APIRouter(include_in_schema=False)


@router.get("/docs")
async def documentation() -> HTMLResponse:
    """Authorize only the framework-generated script; no unsafe-inline policy."""
    response = get_swagger_ui_html(openapi_url="/openapi.json", title="Gatherly AI API")
    body = bytes(response.body).decode()
    hashes = " ".join(
        "'sha256-"
        + base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
        + "'"
        for script in re.findall(r"<script>(.*?)</script>", body, re.DOTALL)
    )
    response.headers["content-security-policy"] = (
        "default-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
        f"script-src https://cdn.jsdelivr.net {hashes}; "
        "style-src https://cdn.jsdelivr.net; connect-src 'self'; "
        "img-src 'self' data: https://fastapi.tiangolo.com; form-action 'none'"
    )
    return response


@router.get("/redoc")
async def reference_alias() -> RedirectResponse:
    """Keep the previous reference URL pointing to the single secured docs UI."""
    return RedirectResponse("/docs")
