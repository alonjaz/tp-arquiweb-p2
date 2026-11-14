from app.config import SITE_ROOT, PING_ENDPOINT

def to_dict(row):
    code = str(row["code"])
    uuid = str(row["code"])
    status = row["status"]
    started = status == "started"
    if status == "started":
        status = "up"

    timeout = int(row["timeout"].total_seconds())
    grace = int(row["grace"].total_seconds())

    last_ping = None
    if row["last_ping"]:
        last_ping = row["last_ping"].strftime("%Y-%m-%dT%H:%M:%S+00:00")

    next_ping = None
    if last_ping and status in ("up", "late", "grace"):
        from datetime import timedelta
        next_ts = row["last_ping"] + row["timeout"]
        next_ping = next_ts.strftime("%Y-%m-%dT%H:%M:%S+00:00")

    last_duration = None
    if row["last_duration"]:
        last_duration = int(row["last_duration"].total_seconds())

    badge_key = str(row["badge_key"])

    result = {
        "name": row["name"],
        "slug": row["slug"],
        "tags": row["tags"],
        "desc": row["desc"],
        "grace": grace,
        "n_pings": row["n_pings"],
        "status": status,
        "started": started,
        "last_ping": last_ping,
        "next_ping": next_ping,
        "manual_resume": row["manual_resume"],
        "methods": row["methods"],
        "subject": row.get("subject", ""),
        "subject_fail": row.get("subject_fail", ""),
        "start_kw": row["start_kw"],
        "success_kw": row["success_kw"],
        "failure_kw": row["failure_kw"],
        "filter_subject": row["filter_subject"],
        "filter_body": row["filter_body"],
        "filter_http_body": row.get("filter_http_body", False),
        "filter_default_fail": row.get("filter_default_fail", False),
        "badge_url": f"{SITE_ROOT}/b/2/{badge_key}.svg",
        "uuid": uuid,
        "ping_url": f"{PING_ENDPOINT}/{uuid}",
        "update_url": f"{SITE_ROOT}/api/v3/checks/{uuid}",
        "pause_url": f"{SITE_ROOT}/api/v3/checks/{uuid}/pause",
        "resume_url": f"{SITE_ROOT}/api/v3/checks/{uuid}/resume",
        "channels": "",
        "timeout": timeout,
    }
    if row["kind"] == "cron":
        result["schedule"] = row["schedule"]
        result["tz"] = row["tz"]
    return result
