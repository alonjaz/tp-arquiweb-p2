import os

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    # con "with" corre el startup de la app (abre el pool)
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def api_key():
    key = os.environ.get("TEST_API_KEY")
    if not key:
        pytest.skip("falta TEST_API_KEY")
    return key


@pytest.fixture
def auth_headers(api_key):
    return {"X-Api-Key": api_key}
