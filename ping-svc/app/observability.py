import datetime, json, logging, sys, time, uuid
from contextvars import ContextVar

from fastapi import Request
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

from app.config import settings

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

class JsonFormatter(logging.Formatter):
    def format(self, r):
        data = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "level": r.levelname,
            "service": settings.service_name,
            "request_id": request_id_var.get(),
            "message": r.getMessage(),
        }
        if r.exc_info:
            data["exc"] = self.formatException(r.exc_info)
        return json.dumps(data, ensure_ascii=False)

def setup_logging():
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonFormatter())
    logging.basicConfig(level=settings.log_level, handlers=[h], force=True)
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers = [h]
    logging.getLogger("uvicorn.access").disabled = True   # lo reemplaza nuestro middleware

REQUESTS = Counter("http_requests_total", "Peticiones HTTP",
                   ["service", "method", "route", "status"])
LATENCY = Histogram("http_request_duration_seconds", "Latencia HTTP",
                    ["service", "method", "route"])

async def observability_middleware(request: Request, call_next):
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())
    token = request_id_var.set(rid)
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = rid
        return response
    finally:
        route = request.scope.get("route")
        path = route.path if route else "unmatched"
        elapsed = time.perf_counter() - start
        if path != "/metrics":
            LATENCY.labels(settings.service_name, request.method, path).observe(elapsed)
            REQUESTS.labels(settings.service_name, request.method, path, str(status)).inc()
        logging.getLogger(settings.service_name).info(
            f"{request.method} {path} {status} {elapsed*1000:.1f}ms")
        request_id_var.reset(token)

def metrics_endpoint():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

