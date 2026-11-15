import os

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "hc")
DB_USER = os.environ.get("DB_USER", "hcuser")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
PORT = int(os.environ.get("PORT", "8001"))
SITE_ROOT = os.environ.get("SITE_ROOT", "http://localhost:8001")
PING_ENDPOINT = os.environ.get("PING_ENDPOINT", "http://localhost:8001/ping")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "checks-svc")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
