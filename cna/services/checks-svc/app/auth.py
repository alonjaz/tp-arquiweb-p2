from fastapi import Request, HTTPException
from app.database import get_conn, put_conn

def get_project(request: Request):
    api_key = request.headers.get("X-Api-Key", "")
    if len(api_key) != 32:
        raise HTTPException(status_code=401, detail="missing api key")
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM accounts_project WHERE api_key = %s",
            (api_key,),
        )
        row = cur.fetchone()
        cur.close()
    finally:
        put_conn(conn)
    if row is None:
        raise HTTPException(status_code=401, detail="wrong api key")
    return row[0]
