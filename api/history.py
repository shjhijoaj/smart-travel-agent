"""Local SQLite history, separated by a browser's anonymous session cookie."""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


@contextmanager
def database():
    path = Path(os.getenv("TRAVEL_DB_PATH", str(Path(__file__).parent.parent / "data" / "travel.db")))
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        # WAL allows reads while a short write is in progress; busy_timeout avoids
        # transient "database is locked" errors when telemetry and history overlap.
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("""CREATE TABLE IF NOT EXISTS plans (
            id TEXT PRIMARY KEY, owner TEXT NOT NULL, created_at TEXT NOT NULL,
            request TEXT NOT NULL, result TEXT NOT NULL, parent_id TEXT)""")
        conn.execute("CREATE INDEX IF NOT EXISTS plans_owner ON plans(owner, created_at DESC)")
        yield conn
        conn.commit()
    finally:
        conn.close()


def save(owner, request, result, parent_id=None):
    record = dict(id=uuid4().hex, created_at=datetime.now(timezone.utc).isoformat(),
                  request=request, result=result, parent_id=parent_id)
    with database() as conn:
        conn.execute("INSERT INTO plans VALUES (?, ?, ?, ?, ?, ?)",
                     (record['id'], owner, record['created_at'], json.dumps(request, ensure_ascii=False),
                      json.dumps(result, ensure_ascii=False), parent_id))
    return record


def get(owner, plan_id):
    with database() as conn:
        row = conn.execute("SELECT * FROM plans WHERE owner=? AND id=?", (owner, plan_id)).fetchone()
    if row is None:
        return None
    return dict(id=row['id'], created_at=row['created_at'], request=json.loads(row['request']),
                result=json.loads(row['result']), parent_id=row['parent_id'])


def list_plans(owner, limit=100, query='', offset=0):
    with database() as conn:
        term='%'+query.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
        rows = conn.execute("SELECT id, created_at, request, parent_id FROM plans WHERE owner=? AND request LIKE ? ESCAPE '\\' ORDER BY created_at DESC LIMIT ? OFFSET ?",
                            (owner, term, limit, offset)).fetchall()
    return [dict(id=row['id'], created_at=row['created_at'], request=json.loads(row['request']),
                 parent_id=row['parent_id']) for row in rows]


def delete(owner, plan_id):
    with database() as conn:
        count = conn.execute("DELETE FROM plans WHERE owner=? AND id=?", (owner, plan_id)).rowcount
    return count > 0


def update_result(owner, plan_id, result):
    with database() as conn:
        count = conn.execute("UPDATE plans SET result=? WHERE owner=? AND id=?",
                             (json.dumps(result, ensure_ascii=False), owner, plan_id)).rowcount
    return count > 0
