import uuid as _uuid
from datetime import datetime, timezone, timedelta
from psycopg.rows import dict_row
from app.database import get_conn, put_conn

def _interval(seconds):
    return timedelta(seconds=seconds)

def list_checks(project_id, tag=None, slug=None):
    conn = get_conn()
    try:
        cur = conn.cursor(row_factory=dict_row)
        sql = "SELECT * FROM api_check WHERE project_id = %s"
        params = [project_id]
        if tag:
            sql += " AND tags LIKE %s"
            params.append(f"%{tag}%")
        if slug:
            sql += " AND slug = %s"
            params.append(slug)
        sql += " ORDER BY created"
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        put_conn(conn)

def get_check(project_id, code):
    conn = get_conn()
    try:
        cur = conn.cursor(row_factory=dict_row)
        cur.execute(
            "SELECT * FROM api_check WHERE code = %s AND project_id = %s",
            (code, project_id),
        )
        row = cur.fetchone()
        cur.close()
        return row
    finally:
        put_conn(conn)

def create_check(project_id, data):
    code = _uuid.uuid4()
    badge_key = _uuid.uuid4()
    now = datetime.now(timezone.utc)
    kind = "cron" if data.get("schedule") else "simple"
    schedule = data.get("schedule") or "* * * * *"
    slug = (data.get("name") or "").lower().replace(" ", "-")[:50]
    timeout = _interval(data.get("timeout") or 86400)
    grace = _interval(data.get("grace") or 3600)

    conn = get_conn()
    try:
        cur = conn.cursor(row_factory=dict_row)
        cur.execute("""
            INSERT INTO api_check (
                code, project_id, name, slug, tags, "desc",
                timeout, grace, schedule, tz, kind, status,
                n_pings, has_confirmation_link, manual_resume,
                methods, created, badge_key,
                start_kw, success_kw, failure_kw,
                filter_subject, filter_body, filter_http_body,
                filter_default_fail
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, 'new',
                0, false, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, false,
                false
            ) RETURNING *
        """, (
            code, project_id,
            data.get("name") or "", slug,
            data.get("tags") or "", data.get("desc") or "",
            timeout, grace, schedule,
            data.get("tz") or "UTC", kind,
            bool(data.get("manual_resume")),
            data.get("methods") or "", now, badge_key,
            data.get("start_kw") or "",
            data.get("success_kw") or "",
            data.get("failure_kw") or "",
            bool(data.get("filter_subject")),
            bool(data.get("filter_body")),
        ))
        row = cur.fetchone()
        conn.commit()
        cur.close()
        return row
    except Exception:
        conn.rollback()
        raise
    finally:
        put_conn(conn)

ALLOWED_FIELDS = {
    "name", "tags", "desc", "timeout", "grace", "schedule", "tz",
    "manual_resume", "methods", "start_kw", "success_kw", "failure_kw",
    "filter_subject", "filter_body",
}

def update_check(project_id, code, data):
    fields = []
    params = []
    for key, val in data.items():
        if val is None or key not in ALLOWED_FIELDS:
            continue
        if key == "timeout":
            fields.append('"timeout" = %s')
            params.append(_interval(val))
        elif key == "grace":
            fields.append('"grace" = %s')
            params.append(_interval(val))
        elif key == "schedule":
            fields.append('"schedule" = %s')
            fields.append('"kind" = \'cron\'')
            params.append(val)
        else:
            fields.append(f'"{key}" = %s')
            params.append(val)
    if not fields:
        return get_check(project_id, code)
    params.extend([code, project_id])
    conn = get_conn()
    try:
        cur = conn.cursor(row_factory=dict_row)
        sql = (
            f"UPDATE api_check SET {', '.join(fields)} "
            "WHERE code = %s AND project_id = %s RETURNING *"
        )
        cur.execute(sql, params)
        row = cur.fetchone()
        conn.commit()
        cur.close()
        return row
    except Exception:
        conn.rollback()
        raise
    finally:
        put_conn(conn)

def delete_check(project_id, code):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM api_check WHERE code = %s AND project_id = %s",
            (code, project_id),
        )
        row = cur.fetchone()
        if not row:
            return False
        check_id = row[0]
        cur.execute("DELETE FROM api_channel_checks WHERE check_id = %s", (check_id,))
        cur.execute("DELETE FROM api_flip WHERE owner_id = %s", (check_id,))
        cur.execute("DELETE FROM api_notification WHERE owner_id = %s", (check_id,))
        cur.execute("DELETE FROM api_ping WHERE owner_id = %s", (check_id,))
        cur.execute("DELETE FROM api_check WHERE id = %s", (check_id,))
        conn.commit()
        cur.close()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        put_conn(conn)
