"""ping-svc: recepción de pings de Healthchecks (/ping/<uuid>)."""
import ipaddress
import logging
import os
import uuid
from email.utils import formatdate

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import PlainTextResponse, Response

from app import db
from app.observability import ObservabilityMiddleware, metrics_endpoint, setup_logging

setup_logging()
log = logging.getLogger("ping-svc")

app = FastAPI(title="ping-svc", docs_url=None, redoc_url=None)
app.add_middleware(ObservabilityMiddleware)
app.add_api_route("/metrics", metrics_endpoint, methods=["GET"], include_in_schema=False)

METHODS = ["GET", "HEAD", "POST", "PUT", "OPTIONS"]
CORS = {"Access-Control-Allow-Origin": "*"}
MAX_BODY = int(os.getenv("PING_BODY_LIMIT", "10000"))  # = settings.PING_BODY_LIMIT


def _text(body: str, status: int = 200) -> Response:
    """Mismas cabeceras que la vista ping() de Django (tipo, CORS, caché, límite de cuerpo)."""
    headers = {
        **CORS,
        "Ping-Body-Limit": str(MAX_BODY),
        "Expires": formatdate(usegmt=True),
        "Cache-Control": "max-age=0, no-cache, no-store, must-revalidate, private",
    }
    return Response(body, status_code=status, headers=headers,
                    media_type="text/html; charset=utf-8")


def parse_suffix(suffix):
    """'' -> success; start/fail/log; <int> -> exitstatus (>255 lo rechaza db). None si inválido."""
    if suffix in (None, ""):
        return ("success", None)
    if suffix in ("start", "fail", "log"):
        return (suffix, None)
    if suffix.isdigit():
        return ("success", int(suffix))
    return None


def clean_remote_addr(raw):
    addr = raw.split(",")[0].strip()
    try:
        ipaddress.ip_address(addr)
    except ValueError:
        parts = addr.split(".")
        if len(parts) == 4 and ":" in parts[-1]:  # ipv4:puerto (Azure)
            addr = addr.split(":")[0]
    return addr


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    try:
        db.ping_db()
    except Exception as exc:  # noqa: BLE001
        log.error("readyz: %s", exc)
        return PlainTextResponse("db unavailable", status_code=503)
    return {"status": "ready"}


@app.api_route("/ping/{code}", methods=METHODS)
@app.api_route("/ping/{code}/", methods=METHODS)
@app.api_route("/ping/{code}/{suffix}", methods=METHODS)
@app.api_route("/ping/{code}/{suffix}/", methods=METHODS)
async def ping(request: Request, code: str, suffix: str = ""):
    try:
        code_uuid = uuid.UUID(code)
    except ValueError:
        return _text("not found", 404)
    parsed = parse_suffix(suffix)
    if parsed is None:
        return _text("not found", 404)
    action, exitstatus = parsed

    rid = None
    if "rid" in request.query_params:
        try:
            rid = uuid.UUID(request.query_params["rid"])
        except ValueError:
            return _text("invalid url format", 400)

    body = (await request.body())[:MAX_BODY]
    fwd = request.headers.get("x-forwarded-for")
    remote = clean_remote_addr(fwd if fwd else (request.client.host if request.client else ""))
    scheme = request.headers.get("x-forwarded-proto", "http")

    try:
        result = await run_in_threadpool(
            db.record_ping, code_uuid, action, exitstatus, scheme, remote,
            request.method, request.headers.get("user-agent", ""), body, rid,
        )
    except Exception as exc:  # noqa: BLE001
        log.error("record_ping falló: %s", exc)
        return _text("service unavailable", 503)

    if result == db.NOT_FOUND:
        return _text("not found", 404)
    if result == db.BAD_REQUEST:
        return _text("invalid url format", 400)
    return _text("OK")
