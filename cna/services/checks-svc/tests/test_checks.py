import uuid

import pytest

BASE = "/api/v3/checks/"


def _code(check):
    if check.get("uuid"):
        return check["uuid"]
    return check["update_url"].rstrip("/").split("/")[-1]


@pytest.fixture
def check_temporal(client, auth_headers):
    r = client.post(BASE, json={"name": "pytest-temporal", "timeout": 3600, "grace": 900},
                    headers=auth_headers)
    assert r.status_code == 201, r.text
    code = _code(r.json())
    yield code
    client.delete(f"{BASE}{code}", headers=auth_headers)


def test_listar(client, auth_headers):
    r = client.get(BASE, headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json()["checks"], list)


def test_obtener(client, auth_headers, check_temporal):
    r = client.get(f"{BASE}{check_temporal}", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "pytest-temporal"
    assert data["timeout"] == 3600
    assert data["grace"] == 900


def test_aparece_en_listado(client, auth_headers, check_temporal):
    r = client.get(BASE, headers=auth_headers)
    assert "pytest-temporal" in [c["name"] for c in r.json()["checks"]]


@pytest.mark.parametrize("metodo", ["POST", "PUT"])
def test_actualizar(client, auth_headers, check_temporal, metodo):
    r = client.request(metodo, f"{BASE}{check_temporal}",
                       json={"name": "pytest-renombrado", "timeout": 7200},
                       headers=auth_headers)
    assert r.status_code == 200, r.text
    r2 = client.get(f"{BASE}{check_temporal}", headers=auth_headers)
    assert r2.json()["name"] == "pytest-renombrado"
    assert r2.json()["timeout"] == 7200


def test_borrar(client, auth_headers, check_temporal):
    assert client.delete(f"{BASE}{check_temporal}", headers=auth_headers).status_code == 200
    assert client.get(f"{BASE}{check_temporal}", headers=auth_headers).status_code == 404


def test_inexistente(client, auth_headers):
    r = client.get(f"{BASE}{uuid.uuid4()}", headers=auth_headers)
    assert r.status_code == 404
