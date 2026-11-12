import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app import db, main

client = TestClient(main.app)
CODE = str(uuid.uuid4())


def fake(result=db.OK, calls=None):
    def _f(*args):
        if calls is not None:
            calls.append(args)
        return result
    return _f


def test_healthz():
    assert client.get("/healthz").json() == {"status": "ok"}


def test_ping_ok(monkeypatch):
    calls = []
    monkeypatch.setattr(db, "record_ping", fake(db.OK, calls))
    r = client.get(f"/ping/{CODE}")
    assert r.status_code == 200 and r.text == "OK"
    assert calls[0][1] == "success"


def test_ping_unknown_check_is_404(monkeypatch):
    monkeypatch.setattr(db, "record_ping", fake(db.NOT_FOUND))
    assert client.get(f"/ping/{CODE}").status_code == 404


def test_invalid_uuid_is_404():
    assert client.get("/ping/no-es-uuid").status_code == 404


def test_start_fail_exitstatus(monkeypatch):
    calls = []
    monkeypatch.setattr(db, "record_ping", fake(db.OK, calls))
    client.post(f"/ping/{CODE}/start")
    client.get(f"/ping/{CODE}/fail")
    client.get(f"/ping/{CODE}/2")
    assert [c[1] for c in calls] == ["start", "fail", "success"]
    assert calls[2][2] == 2  # exitstatus (la vista decide "fail" dentro de db)


def test_post_body_and_xff(monkeypatch):
    calls = []
    monkeypatch.setattr(db, "record_ping", fake(db.OK, calls))
    client.post(f"/ping/{CODE}", content=b"hola",
                headers={"X-Forwarded-For": "1.2.3.4, 9.9.9.9"})
    assert calls[0][4] == "1.2.3.4" and calls[0][7] == b"hola"


def test_db_error_is_503(monkeypatch):
    def boom(*a):
        raise RuntimeError("db caída")
    monkeypatch.setattr(db, "record_ping", boom)
    assert client.get(f"/ping/{CODE}").status_code == 503


def test_going_down_after_simple_up():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    r = db.going_down_after("up", "simple", now, None, timedelta(days=1),
                            timedelta(hours=1), "", "UTC")
    assert r == now + timedelta(days=1, hours=1)


def test_going_down_after_down_is_none():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert db.going_down_after("down", "simple", now, None, timedelta(days=1),
                               timedelta(hours=1), "", "UTC") is None


def test_going_down_after_new_not_running_is_none():
    assert db.going_down_after("new", "simple", None, None, timedelta(days=1),
                               timedelta(hours=1), "", "UTC") is None


def test_going_down_after_running_uses_last_start():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    r = db.going_down_after("new", "simple", None, start, timedelta(days=1),
                            timedelta(hours=1), "", "UTC")
    assert r == start + timedelta(hours=1)


def test_exitstatus_over_255_is_400(monkeypatch):
    monkeypatch.setattr(db, "record_ping", fake(db.BAD_REQUEST))
    assert client.get(f"/ping/{CODE}/300").status_code == 400


def test_remote_addr_strips_port():
    assert main.clean_remote_addr("1.2.3.4:5555, 9.9.9.9") == "1.2.3.4"
