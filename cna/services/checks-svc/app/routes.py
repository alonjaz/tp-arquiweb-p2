import logging
import time
import uuid as _uuid
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from prometheus_client import Counter, Histogram, generate_latest
from app.auth import get_project
from app.models import CheckIn, CheckUpdate
from app.repository import list_checks, get_check, create_check, update_check, delete_check
from app.serializers import to_dict
from app.database import get_conn, put_conn

logger = logging.getLogger(__name__)

REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests",
    ["method", "path", "status"]
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds", "HTTP request duration",
    ["method", "path"]
)

router = APIRouter()

@router.get("/healthz")
def healthz():
    return {"status": "alive"}

@router.get("/readyz")
def readyz():
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="database not ready")
    finally:
        if conn:
            put_conn(conn)

@router.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type="text/plain; version=0.0.4")

@router.get("/api/v3/checks/")
def api_list_checks(request: Request, tag: str = None, slug: str = None, project_id: int = Depends(get_project)):
    rows = list_checks(project_id, tag=tag, slug=slug)
    return {"checks": [to_dict(r) for r in rows]}

@router.post("/api/v3/checks/", status_code=201)
def api_create_check(request: Request, body: CheckIn, response: Response, project_id: int = Depends(get_project)):
    if body.unique:
        existing = list_checks(project_id)
        for row in existing:
            match = True
            for field in body.unique:
                if field == "name" and row["name"] != body.name:
                    match = False
                if field == "tags" and row["tags"] != body.tags:
                    match = False
                if field == "timeout" and int(row["timeout"].total_seconds()) != body.timeout:
                    match = False
            if match:
                response.status_code = 200
                return to_dict(row)
    data = body.model_dump(exclude={"unique", "channels"})
    row = create_check(project_id, data)
    return to_dict(row)

@router.get("/api/v3/checks/{code}")
def api_get_check(code: str, project_id: int = Depends(get_project)):
    try:
        _uuid.UUID(code)
    except ValueError:
        raise HTTPException(status_code=404, detail="not found")
    row = get_check(project_id, code)
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    return to_dict(row)

@router.post("/api/v3/checks/{code}")
def api_update_check_post(code: str, body: CheckUpdate, project_id: int = Depends(get_project)):
    try:
        _uuid.UUID(code)
    except ValueError:
        raise HTTPException(status_code=404, detail="not found")
    row = get_check(project_id, code)
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    data = body.model_dump(exclude_none=True, exclude={"channels"})
    updated = update_check(project_id, code, data)
    return to_dict(updated)

@router.put("/api/v3/checks/{code}")
def api_update_check_put(code: str, body: CheckUpdate, project_id: int = Depends(get_project)):
    return api_update_check_post(code, body, project_id)

@router.delete("/api/v3/checks/{code}")
def api_delete_check(code: str, project_id: int = Depends(get_project)):
    try:
        _uuid.UUID(code)
    except ValueError:
        raise HTTPException(status_code=404, detail="not found")
    deleted = delete_check(project_id, code)
    if not deleted:
        raise HTTPException(status_code=404, detail="not found")
    return Response(content='{"ok": true}', media_type="application/json")
