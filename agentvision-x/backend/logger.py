"""Execution logger — saves logs to JSON/SQLite."""
import json
import os
import sqlite3
from datetime import datetime
from typing import List, Dict, Any

LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

DB_PATH = os.path.join(LOGS_DIR, "execution_logs.db")
JSON_PATH = os.path.join(LOGS_DIR, "execution_history.json")


def _init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS execution_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            step_name TEXT,
            prompt TEXT,
            input_data TEXT,
            output_data TEXT,
            tokens INTEGER,
            status TEXT,
            execution_time REAL,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()


_init_db()


def save_step_log(session_id: str, step: Dict[str, Any]):
    """Save a step log to SQLite and JSON."""
    # SQLite
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO execution_logs 
        (session_id, step_name, prompt, input_data, output_data, tokens, status, execution_time, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id,
        step.get("name", ""),
        step.get("prompt", ""),
        step.get("input_data", ""),
        step.get("output_data", ""),
        step.get("tokens", 0),
        step.get("status", ""),
        step.get("execution_time", 0.0),
        step.get("timestamp", datetime.utcnow().isoformat())
    ))
    conn.commit()
    conn.close()

    # JSON append
    history = []
    if os.path.exists(JSON_PATH):
        try:
            with open(JSON_PATH, "r") as f:
                history = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            history = []

    history.append({"session_id": session_id, **step})
    with open(JSON_PATH, "w") as f:
        json.dump(history, f, indent=2, default=str)


def get_execution_history(limit: int = 50) -> List[Dict]:
    """Retrieve recent execution logs."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM execution_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    columns = ["id", "session_id", "step_name", "prompt", "input_data",
               "output_data", "tokens", "status", "execution_time", "timestamp"]
    return [dict(zip(columns, row)) for row in rows]
