import logging
import time
import uuid
from fastapi import FastAPI, Request
from app.config import SERVICE_NAME
from app.database import init_pool, close_pool
from app.logging_config import setup_logging
from app.routes import router, REQUEST_COUNT, REQUEST_DURATION

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title=SERVICE_NAME)
app.include_router(router)

@app.on_event("startup")
def startup():
    init_pool()
    logger.info("checks-svc started")

@app.on_event("shutdown")
def shutdown():
    close_pool()
    logger.info("checks-svc stopped")

@app.middleware("http")
async def metrics_and_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    path = request.scope.get("path", request.url.path)
    for route in router.routes:
        if hasattr(route, "path") and route.path == path:
            break
        if hasattr(route, "path_regex") and route.path_regex.match(path):
            path = route.path
            break
    REQUEST_COUNT.labels(
        method=request.method,
        path=path,
        status=response.status_code,
    ).inc()
    REQUEST_DURATION.labels(
        method=request.method,
        path=path,
    ).observe(duration)
    response.headers["X-Request-ID"] = request_id
    return response
