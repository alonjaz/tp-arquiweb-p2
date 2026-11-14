from psycopg_pool import ConnectionPool
from app.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

pool = None

def init_pool():
    global pool
    conninfo = (
        f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} "
        f"user={DB_USER} password={DB_PASSWORD}"
    )
    pool = ConnectionPool(conninfo, min_size=2, max_size=10, open=True)

def get_conn():
    return pool.getconn()

def put_conn(conn):
    pool.putconn(conn)

def close_pool():
    if pool:
        pool.close()
