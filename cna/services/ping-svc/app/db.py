"""Acceso a PostgreSQL de ping-svc.

Replica fielmente (Healthchecks v4.0):
  - hc/api/views.py::ping()            -> reglas de decisión (acción, métodos, keywords)
  - hc/api/models.py::Check.ping()     -> actualización de api_check + alta de api_ping/api_flip
  - Check.get_grace_start() / going_down_after() / create_flip() / prune()
  - hc/lib/string.py::match_keywords

Dependencias externas (PyPI, las mismas que usa Healthchecks):
  - cronsim      -> checks tipo "cron"
  - oncalendar   -> checks tipo "oncalendar"
"""
import ipaddress
import logging
from datetime import datetime, timedelta, timezone
import os
from zoneinfo import ZoneInfo

from psycopg_pool import ConnectionPool

log = logging.getLogger("ping-svc")

OK, NOT_FOUND, BAD_REQUEST = "ok", "not_found", "bad_request"
NEVER = datetime(3000, 1, 1, tzinfo=timezone.utc)  # igual que el sentinel de hc

_pool = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=os.environ["DATABASE_URL"],
            min_size=int(os.getenv("DB_POOL_MIN", "2")),
            max_size=int(os.getenv("DB_POOL_MAX", "10")),
            open=True,
        )
    return _pool


def ping_db() -> bool:
    with get_pool().connection() as conn:
        conn.execute("SELECT 1")
    return True


def match_keywords(haystack: str, keywords: str) -> bool:
    """Idéntica a hc/lib/string.py::match_keywords."""
    for k in keywords.split(","):
        k = k.strip()
        if k and k in haystack:
            return True
    return False


def valid_inet(addr):
    """api_ping.remote_addr es inet: None si no es una IP válida."""
    try:
        ipaddress.ip_address(addr)
        return addr
    except (ValueError, TypeError):
        return None


def get_grace_start(status, kind, last_ping, last_start, timeout, schedule, tz):
    """Idéntica a Check.get_grace_start(with_started=True)."""
    result = NEVER

    if kind == "simple" and status == "up":
        result = last_ping + timeout
    elif kind == "cron" and status == "up":
        from cronsim import CronSim

        last_local = last_ping.astimezone(ZoneInfo(tz))
        result = next(CronSim(schedule, last_local)).astimezone(timezone.utc)
    elif kind == "oncalendar" and status == "up":
        from oncalendar import OnCalendar  # paquete PyPI, dependencia de Healthchecks

        last_local = last_ping.astimezone(ZoneInfo(tz))
        try:
            result = next(OnCalendar(schedule, last_local)).astimezone(timezone.utc)
        except StopIteration:
            result = NEVER

    if last_start and status != "down":
        result = min(result, last_start)

    return result if result != NEVER else None


def going_down_after(status, kind, last_ping, last_start, timeout, grace, schedule, tz):
    """Idéntica a Check.going_down_after()."""
    gs = get_grace_start(status, kind, last_ping, last_start, timeout, schedule, tz)
    return gs + grace if gs is not None else None


def record_ping(code, action, exitstatus, scheme, remote_addr, method, ua, body, rid):
    """action: 'success' | 'start' | 'fail' | 'log' | 'ign'.
    Devuelve OK / NOT_FOUND / BAD_REQUEST (mismo orden de validación que views.ping)."""
    with get_pool().connection() as conn:  # una transacción (= transaction.atomic)
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, project_id, status, kind, timeout, grace, schedule, tz,
                          manual_resume, methods, filter_http_body, failure_kw,
                          success_kw, start_kw, filter_default_fail,
                          last_ping, last_start, last_start_rid, last_duration
                   FROM api_check WHERE code = %s FOR UPDATE""",
                (code,),
            )
            row = cur.fetchone()
            if row is None:
                return NOT_FOUND
            (cid, project_id, status, kind, timeout, grace, schedule, tz,
             manual_resume, methods, filter_http_body, failure_kw, success_kw,
             start_kw, filter_default_fail, last_ping, last_start,
             last_start_rid, last_duration) = row

            # --- decisión de la vista (views.ping) ---
            if exitstatus is not None and exitstatus > 255:
                return BAD_REQUEST
            if exitstatus is not None and exitstatus > 0:
                action = "fail"
            if methods == "POST" and method != "POST":
                action = "ign"
            if action != "ign" and filter_http_body:
                text = body.decode()
                if failure_kw and match_keywords(text, failure_kw):
                    action = "fail"
                elif success_kw and match_keywords(text, success_kw):
                    action = "success"
                elif start_kw and match_keywords(text, start_kw):
                    action = "start"
                elif filter_default_fail:
                    action = "fail"
                else:
                    action = "ign"

            # --- Check.ping() ---
            now = datetime.now(timezone.utc)
            if status == "paused" and manual_resume:
                action = "ign"

            if action == "start":
                last_start, last_start_rid = now, rid
            elif action in ("ign", "log"):
                pass
            else:
                last_ping = now
                last_duration = None
                if last_start:
                    if last_start_rid == rid:
                        last_duration = last_ping - last_start
                        last_start = None
                    elif action == "fail" or rid is None:
                        last_start = None

                new_status = "down" if action == "fail" else "up"
                if status != new_status:  # = create_flip()
                    cur.execute(
                        """INSERT INTO api_flip (owner_id, created, processed,
                                                 old_status, new_status, reason)
                           VALUES (%s, %s, NULL, %s, %s, %s)""",
                        (cid, datetime.now(timezone.utc), status, new_status,
                         "fail" if action == "fail" else ""),
                    )
                    status = new_status

            alert_after = going_down_after(
                status, kind, last_ping, last_start, timeout, grace, schedule, tz)
            has_link = "confirm" in body.decode(errors="replace").lower()

            cur.execute(
                """UPDATE api_check
                   SET last_ping=%s, last_duration=%s, last_start=%s,
                       last_start_rid=%s, status=%s, alert_after=%s,
                       n_pings = n_pings + 1, has_confirmation_link=%s
                   WHERE id=%s RETURNING n_pings""",
                (last_ping, last_duration, last_start, last_start_rid, status,
                 alert_after, has_link, cid),
            )
            n = cur.fetchone()[0]

            # Sin S3: el cuerpo va siempre en body_raw (como el original sin S3_BUCKET)
            cur.execute(
                """INSERT INTO api_ping (owner_id, n, created, kind, scheme,
                                         remote_addr, method, ua, rid,
                                         exitstatus, body_raw)
                   VALUES (%s,%s,%s,%s,%s,%s::inet,%s,%s,%s,%s,%s)""",
                (cid, n, now,
                 action if action in ("start", "fail", "ign", "log") else None,
                 scheme, valid_inet(remote_addr), method, (ua or "")[:200], rid,
                 exitstatus, body),
            )

    # Igual que el original: fuera de la transacción, cada 100 pings.
    if n % 100 == 0:
        try:
            prune(cid, project_id, n)
        except Exception as exc:  # noqa: BLE001  (no debe fallar el ping)
            log.error("prune falló: %s", exc)
    return OK


def prune(cid, project_id, n_pings):
    """Idéntica a Check.prune() (sin S3)."""
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT pf.ping_log_limit FROM accounts_profile pf
                   JOIN accounts_project pr ON pr.owner_id = pf.user_id
                   WHERE pr.id = %s""",
                (project_id,),
            )
            limit = cur.fetchone()[0]
            threshold = n_pings - limit
            cur.execute("DELETE FROM api_ping WHERE owner_id=%s AND n <= %s",
                        (cid, threshold))
            cur.execute(
                "SELECT created FROM api_ping WHERE owner_id=%s ORDER BY created LIMIT 1",
                (cid,),
            )
            row = cur.fetchone()
            if row:
                oldest = row[0]
                cur.execute(
                    "DELETE FROM api_notification WHERE owner_id=%s AND created < %s",
                    (cid, oldest),
                )
                flip_threshold = min(oldest, datetime.now(timezone.utc) - timedelta(days=93))
                cur.execute(
                    "DELETE FROM api_flip WHERE owner_id=%s AND created < %s",
                    (cid, flip_threshold),
                )
