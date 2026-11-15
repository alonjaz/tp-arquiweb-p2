URL = "/api/v3/checks/"


def test_sin_api_key(client):
    assert client.get(URL).status_code == 401


def test_api_key_incorrecta(client):
    r = client.get(URL, headers={"X-Api-Key": "x" * 32})
    assert r.status_code == 401


def test_api_key_largo_invalido(client):
    r = client.get(URL, headers={"X-Api-Key": "corta"})
    assert r.status_code == 401


def test_api_key_valida(client, auth_headers):
    assert client.get(URL, headers=auth_headers).status_code == 200
