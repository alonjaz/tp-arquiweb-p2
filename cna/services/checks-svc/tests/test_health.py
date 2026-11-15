def test_healthz(client):
    assert client.get("/healthz").status_code == 200


def test_readyz(client):
    assert client.get("/readyz").status_code == 200


def test_metrics(client):
    client.get("/healthz")
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "http_requests_total" in r.text
    assert "http_request_duration_seconds" in r.text


def test_request_id_se_devuelve(client):
    r = client.get("/healthz", headers={"X-Request-ID": "pytest-req-123"})
    assert r.headers.get("X-Request-ID") == "pytest-req-123"
