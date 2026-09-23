"""FastAPI application entry point for مدربك الخاص backend."""
from __future__ import annotations

import logging
import time
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .routers.api import router

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("coach")

app = FastAPI(
    title="مدربك الخاص — Your Personal Coach API",
    version="1.0.0",
    docs_url="/docs",
)

# ---- simple in-memory rate limiting (per-IP, per-minute). For multi-instance
# production deployments replace with a shared store (e.g. Redis).
_BUCKET: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_PER_MIN = 120
AUTH_RATE_LIMIT_PER_MIN = 10


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    from .settings import get_settings
    if get_settings().env == "test":
        return await call_next(request)
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    key = f"{ip}:auth" if request.url.path.startswith("/api/auth") else ip
    limit = AUTH_RATE_LIMIT_PER_MIN if key.endswith(":auth") else RATE_LIMIT_PER_MIN
    bucket = _BUCKET[key]
    bucket[:] = [t for t in bucket if now - t < 60]
    if len(bucket) >= limit:
        return JSONResponse(status_code=429, content={"detail": "rate_limited"})
    bucket.append(now)
    return await call_next(request)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Never expose stack traces to clients; log server-side without sensitive data.
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "internal_error"})


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(router, prefix="/api")
