# tests/test_ping.py
from fastapi.testclient import TestClient
from app import db
from app.main import app, parse_suffix

client = TestClient(app)
UID = "08e27489-57e1-477c-8017-77d358d36de1"

def test_healthz():
    assert client.get("/healthz").json() == {"status": "ok"}

def test_readyz_ok_y_fail(monkeypatch):
    monkeypatch.setattr(db, "ping_db", lambda: True)
    assert client.get("/readyz").status_code == 200
    def boom(): raise RuntimeError("db down")
    monkeypatch.setattr(db, "ping_db", boom)
    assert client.get("/readyz").status_code == 503

def test_metrics_expone_contador_e_histograma():
    client.get("/healthz")
    t = client.get("/metrics").text
    assert "http_requests_total" in t
    assert "http_request_duration_seconds_bucket" in t

def test_request_id_se_propaga():
    r = client.get("/healthz", headers={"X-Request-ID": "abc-123"})
    assert r.headers["X-Request-ID"] == "abc-123"

def test_ping_ok(monkeypatch):
    monkeypatch.setattr(db, "record_ping", lambda *a: db.OK)
    r = client.get(f"/ping/{UID}")
    assert r.status_code == 200 and r.text == "OK"

def test_ping_uuid_invalido_y_no_encontrado(monkeypatch):
    assert client.get("/ping/no-es-uuid").status_code == 404
    monkeypatch.setattr(db, "record_ping", lambda *a: db.NOT_FOUND)
    assert client.get(f"/ping/{UID}").status_code == 404

def test_ping_db_caida_devuelve_503(monkeypatch):
    def boom(*a): raise RuntimeError
    monkeypatch.setattr(db, "record_ping", boom)
    assert client.get(f"/ping/{UID}").status_code == 503

def test_parse_suffix_y_keywords():
    assert parse_suffix("fail") == ("fail", None)
    assert parse_suffix("3") == ("success", 3)
    assert parse_suffix("xx") is None
    assert db.match_keywords("all OK", "ok, OK")