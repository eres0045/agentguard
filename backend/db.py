"""SQLite audit log — every decision and every testnet tx hash, with explorer links.

Tables:
  audit     — one row per payment attempt (requested, decided, executed/blocked)
  approvals — human-approval queue (pending/approved/rejected/executed)
"""
import sqlite3
import time
from pathlib import Path

EXPLORER_TX = "https://explorer.testnet.near.org/transactions/"

SCHEMA = """
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    actor TEXT NOT NULL,          -- 'agent' | 'human' | 'rogue-harness'
    recipient TEXT NOT NULL,
    amount_near REAL NOT NULL,
    purpose TEXT DEFAULT '',
    verdict TEXT NOT NULL,        -- EXECUTE | QUEUE | BLOCK | APPROVED | REJECTED | KILLED
    reasons TEXT DEFAULT '',
    classifier_score REAL DEFAULT 0,
    tx_hash TEXT,
    explorer_url TEXT,
    status TEXT DEFAULT ''        -- on-chain outcome text, if any
);
CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    recipient TEXT NOT NULL,
    amount_near REAL NOT NULL,
    purpose TEXT DEFAULT '',
    reasons TEXT DEFAULT '',
    classifier_score REAL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending|approved|rejected|executed
    tx_hash TEXT,
    explorer_url TEXT,
    decided_ts REAL
);
"""


class AuditLog:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def record(self, actor, recipient, amount_near, verdict, reasons="",
               classifier_score=0.0, tx_hash=None, status="", purpose=""):
        cur = self.conn.execute(
            """INSERT INTO audit (ts, actor, recipient, amount_near, purpose, verdict,
                                  reasons, classifier_score, tx_hash, explorer_url, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (time.time(), actor, recipient, amount_near, purpose, verdict,
             reasons, classifier_score, tx_hash,
             (EXPLORER_TX + tx_hash) if tx_hash else None, status))
        self.conn.commit()
        return cur.lastrowid

    def queue_approval(self, recipient, amount_near, reasons="",
                       classifier_score=0.0, purpose=""):
        cur = self.conn.execute(
            """INSERT INTO approvals (ts, recipient, amount_near, purpose, reasons,
                                      classifier_score, status)
               VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
            (time.time(), recipient, amount_near, purpose, reasons, classifier_score))
        self.conn.commit()
        return cur.lastrowid

    def set_approval(self, approval_id, status, tx_hash=None):
        self.conn.execute(
            """UPDATE approvals SET status=?, tx_hash=?, explorer_url=?, decided_ts=?
               WHERE id=?""",
            (status, tx_hash, (EXPLORER_TX + tx_hash) if tx_hash else None,
             time.time(), approval_id))
        self.conn.commit()

    def get_approval(self, approval_id):
        row = self.conn.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)).fetchone()
        return dict(row) if row else None

    def pending_approvals(self):
        rows = self.conn.execute(
            "SELECT * FROM approvals WHERE status='pending' ORDER BY ts").fetchall()
        return [dict(r) for r in rows]

    def recent_count(self, seconds=60):
        # One row per on-chain payment: only EXECUTE verdicts count.
        # (The human APPROVED row for the same payment is a decision record,
        # not a second payment — counting it would double-count approvals.)
        row = self.conn.execute(
            "SELECT COUNT(*) c FROM audit WHERE ts > ? AND verdict = 'EXECUTE'",
            (time.time() - seconds,)).fetchone()
        return row["c"]

    def recent(self, limit=100):
        rows = self.conn.execute(
            "SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.conn.close()
