"""PostgreSQL 連線（階段 3、6、7 共用）。

連線目標由 `docker-compose.yml` 提供，只綁 127.0.0.1。
可用環境變數覆寫，供 CI 或其他環境使用。
"""

from __future__ import annotations

import os

import psycopg2

DSN = dict(
    host=os.getenv("PGHOST", "127.0.0.1"),
    port=int(os.getenv("PGPORT", "5432")),
    dbname=os.getenv("PGDATABASE", "broadband"),
    user=os.getenv("PGUSER", "broadband"),
    password=os.getenv("PGPASSWORD", "broadband_local_dev"),
)


def connect():
    return psycopg2.connect(**DSN)


def server_version(conn) -> str:
    with conn.cursor() as cur:
        cur.execute("select version()")
        return cur.fetchone()[0]
