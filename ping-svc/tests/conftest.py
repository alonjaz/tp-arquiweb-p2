# tests/conftest.py
import os
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost/db")