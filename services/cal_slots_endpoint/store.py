import sqlite3
import threading
import time

DB_PATH = "/home/julio/projects/Retell_AI_MCP_connection/cal_slots_endpoint/slots.db"

_lock = threading.Lock()


def _conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init():
    conn = _conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS counters (
            name TEXT PRIMARY KEY,
            value INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS rl (
            ip TEXT NOT NULL,
            window_start REAL NOT NULL,
            count INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (ip, window_start)
        );
    """)
    conn.commit()
    conn.close()


def incr(name: str, n: int = 1):
    with _lock:
        conn = _conn()
        conn.execute(
            "INSERT INTO counters (name, value) VALUES (?, ?) "
            "ON CONFLICT(name) DO UPDATE SET value = value + ?",
            (name, n, n),
        )
        conn.commit()
        conn.close()


def snapshot() -> dict:
    with _lock:
        conn = _conn()
        rows = conn.execute("SELECT name, value FROM counters").fetchall()
        conn.close()
    return {r[0]: r[1] for r in rows}


def rate_limited(ip: str, limit: int) -> bool:
    now = time.time()
    window = 60.0
    window_start = int(now // window) * window
    with _lock:
        conn = _conn()
        conn.execute(
            "DELETE FROM rl WHERE window_start < ?",
            (window_start - window,),
        )
        row = conn.execute(
            "SELECT count FROM rl WHERE ip = ? AND window_start = ?",
            (ip, window_start),
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO rl (ip, window_start, count) VALUES (?, ?, 1)",
                (ip, window_start),
            )
            conn.commit()
            conn.close()
            return False
        new_count = row[0] + 1
        conn.execute(
            "UPDATE rl SET count = ? WHERE ip = ? AND window_start = ?",
            (new_count, ip, window_start),
        )
        conn.commit()
        conn.close()
        return new_count > limit
