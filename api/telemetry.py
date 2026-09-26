"""Small SQLite telemetry ledger for run time, outcome and estimated model cost."""
import json
import sqlite3
import time
from .history import database


def record(owner, operation, started, success, *, model="", tokens=0, cost=0.0, details=None):
    duration = round((time.perf_counter() - started) * 1000, 2)
    with database() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS run_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT NOT NULL, operation TEXT NOT NULL,
            created_at REAL NOT NULL, duration_ms REAL NOT NULL, success INTEGER NOT NULL,
            model TEXT, tokens INTEGER NOT NULL, estimated_cost REAL NOT NULL, details TEXT)""")
        conn.execute("CREATE INDEX IF NOT EXISTS run_events_owner ON run_events(owner, created_at DESC)")
        conn.execute("INSERT INTO run_events(owner,operation,created_at,duration_ms,success,model,tokens,estimated_cost,details) VALUES (?,?,?,?,?,?,?,?,?)",
                     (owner, operation, time.time(), duration, int(success), model, int(tokens), float(cost),
                      json.dumps(details or {}, ensure_ascii=False)))
    return duration


def summary(owner):
    with database() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS run_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT NOT NULL, operation TEXT NOT NULL,
            created_at REAL NOT NULL, duration_ms REAL NOT NULL, success INTEGER NOT NULL,
            model TEXT, tokens INTEGER NOT NULL, estimated_cost REAL NOT NULL, details TEXT)""")
        conn.execute("CREATE INDEX IF NOT EXISTS run_events_owner ON run_events(owner, created_at DESC)")
        row = conn.execute("""SELECT COUNT(*) count, COALESCE(SUM(success),0) successes,
            COALESCE(AVG(duration_ms),0) avg_ms, COALESCE(SUM(tokens),0) tokens,
            COALESCE(SUM(estimated_cost),0) cost FROM run_events WHERE owner=?""", (owner,)).fetchone()
        recent = conn.execute("SELECT operation,duration_ms,success,created_at,details FROM run_events WHERE owner=? ORDER BY id DESC LIMIT 20", (owner,)).fetchall()
    return {"count": row["count"], "successes": row["successes"], "success_rate": round(row["successes"] / row["count"], 3) if row["count"] else 0,
            "avg_duration_ms": round(row["avg_ms"], 2), "tokens": row["tokens"], "estimated_cost": round(row["cost"], 6),
            "recent": [dict(r) for r in recent]}
