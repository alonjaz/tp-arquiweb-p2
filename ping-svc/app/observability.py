"""Observabilidad de ping-svc: logs JSON, X-Request-ID y métricas Prometheus.

Requisitos B2: GET /metrics (contador de peticiones por código + histograma de latencia),
logs JSON a stdout con timestamp, level, service, request_id y message, y propagación
de X-Request-ID.

Con varios workers de uvicorn cada proceso tiene su propio registro; para que /metrics
muestre el total se usa el modo multiproceso de prometheus_client
(PROMETHEUS_MULTIPROC_DIR, un directorio escribible: en Docker, un tmpfs en /prom).
"""
import datetime
import json
import logging
import os
import re
import sys
import time
import uuid
from contextvars import ContextVar

# Debe resolverse ANTES de importar prometheus_client (lee la variable al importarse).
_MP_DIR = os.getenv("PROMETHEUS_MULTIPROC_DIR")
MULTIPROC_OK = bool(_MP_DIR and os.path.isdir(_MP_DIR) and os.access(_MP_DIR, os.W_OK))
if _MP_DIR and not MULTIPROC_OK:
    os.environ.pop("PROMETHEUS_MULTIPROC_DIR")

from fastapi.responses import Response  # noqa: E402
from prometheus_client import (CONTENT_TYPE_LATEST, CollectorRegistry, Counter,  # noqa: E402
                               Histogram, generate_latest, multiprocess)

SERVICE = os.getenv("SERVICE_NAME", "ping-svc")
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
_RID_OK = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
_SKIP = ("/metrics", "/healthz")  # no se cuentan ni se registran (ruido de sondas)


class JsonFormatter(logging.Formatter):
    def format(self, r):
        data = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "level": r.levelname,
            "service": SERVICE,
            "request_id": request_id_var.get(),
            "message": r.getMessage(),
        }
        if r.exc_info:
            data["exc"] = self.formatException(r.exc_info)
        return json.dumps(data, ensure_ascii=False)


def setup_logging():
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonFormatter())
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), handlers=[h], force=True)
    for name in ("uvicorn", "uvicorn.error"):
        lg = logging.getLogger(name)
        lg.handlers, lg.propagate = [h], False
    logging.getLogger("uvicorn.access").disabled = True  # lo reemplaza el middleware
    if _MP_DIR and not MULTIPROC_OK:
        logging.getLogger(SERVICE).warning(
            "PROMETHEUS_MULTIPROC_DIR no es escribible: /metrics será por proceso (montar tmpfs en /prom)")


REQUESTS = Counter("http_requests_total", "Peticiones HTTP",
                   ["service", "method", "route", "status"])
LATENCY = Histogram("http_request_duration_seconds", "Latencia HTTP",
                    ["service", "method", "route"])


class ObservabilityMiddleware:
    """Middleware ASGI puro (menos sobrecarga que BaseHTTPMiddleware)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        rid = ""
        for k, v in scope["headers"]:
            if k == b"x-request-id":
                rid = v.decode("latin-1")
                break
        if not _RID_OK.match(rid):  # ausente o con caracteres raros -> generar uno nuevo
            rid = str(uuid.uuid4())

        token = request_id_var.set(rid)
        start = time.perf_counter()
        status = 500

        async def send_wrapper(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message.setdefault("headers", []).append((b"x-request-id", rid.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            route = scope.get("route")
            path = route.path if route else "unmatched"
            if path not in _SKIP:
                elapsed = time.perf_counter() - start
                method = scope["method"]
                LATENCY.labels(SERVICE, method, path).observe(elapsed)
                REQUESTS.labels(SERVICE, method, path, str(status)).inc()
                logging.getLogger(SERVICE).info(f"{method} {path} {status} {elapsed*1000:.1f}ms")
            request_id_var.reset(token)


def metrics_endpoint():
    if MULTIPROC_OK:
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        data = generate_latest(registry)
    else:
        data = generate_latest()
    return Response(data, media_type=CONTENT_TYPE_LATEST)
