"""SQLite storage — stdlib only, no external DB needed.

Tables:
  leads     — email captures (pricing notify-me fallback + contact)
  packages  — generated ad packages (the product of the create flow)
  events    — lightweight analytics event log (Army web-app pattern:
              every meaningful action writes one row; /api/stats reads it)

Event logging is the analytics layer for this app: page views,
package_created, checkout_click, lead_captured. No third-party tracker,
no cookies, no cost.
"""
import json
import os
import sqlite3
import time
import uuid

import config

_conn = None


def conn():
    global _conn
    if _conn is None:
        path = config.DB_PATH
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        _conn = sqlite3.connect(path, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    return _conn


def init_db():
    c = conn()
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            tier TEXT DEFAULT '',
            source TEXT DEFAULT '',
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS packages (
            id TEXT PRIMARY KEY,
            email TEXT DEFAULT '',
            product_name TEXT NOT NULL,
            payload TEXT NOT NULL,
            video_status TEXT DEFAULT 'stub',
            video_ref TEXT DEFAULT '',
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            props TEXT DEFAULT '',
            created_at REAL NOT NULL
        );
        """
    )
    c.commit()


# ---------- analytics ----------

def log_event(name: str, props: str = "") -> None:
    try:
        c = conn()
        c.execute(
            "INSERT INTO events (name, props, created_at) VALUES (?, ?, ?)",
            (name, props, time.time()),
        )
        c.commit()
    except Exception:
        pass  # analytics must never break the app


def stats() -> dict:
    c = conn()
    out = {}
    for row in c.execute(
        "SELECT name, COUNT(*) AS n FROM events GROUP BY name ORDER BY n DESC"
    ):
        out[row["name"]] = row["n"]
    out["packages_total"] = c.execute("SELECT COUNT(*) FROM packages").fetchone()[0]
    out["leads_total"] = c.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    return out


# ---------- leads ----------

def save_lead(email: str, tier: str = "", source: str = "") -> bool:
    email = (email or "").strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        return False
    c = conn()
    c.execute(
        "INSERT INTO leads (email, tier, source, created_at) VALUES (?, ?, ?, ?)",
        (email, tier, source, time.time()),
    )
    c.commit()
    log_event("lead_captured", f"tier={tier} source={source}")
    return True


# ---------- packages ----------

def new_package_id() -> str:
    return uuid.uuid4().hex[:12]


def save_package(pkg_id: str, email: str, product_name: str, payload: dict,
                 video_status: str, video_ref: str = "") -> None:
    c = conn()
    c.execute(
        "INSERT INTO packages (id, email, product_name, payload, video_status,"
        " video_ref, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (pkg_id, email.strip().lower(), product_name, json.dumps(payload),
         video_status, video_ref, time.time()),
    )
    c.commit()


def get_package(pkg_id: str):
    row = conn().execute(
        "SELECT * FROM packages WHERE id = ?", (pkg_id,)
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["payload"] = json.loads(d["payload"])
    return d


def count_packages_for_email(email: str) -> int:
    if not email:
        return 0
    row = conn().execute(
        "SELECT COUNT(*) AS n FROM packages WHERE email = ?",
        (email.strip().lower(),),
    ).fetchone()
    return row["n"]


def recent_packages(limit: int = 6):
    rows = conn().execute(
        "SELECT id, product_name, created_at FROM packages ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]
