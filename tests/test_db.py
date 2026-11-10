"""Audit-log (SQLite) unit tests — no chain, no network."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from db import AuditLog  # noqa: E402


def test_record_and_recent(tmp_path):
    log = AuditLog(tmp_path / "a.db")
    log.record("agent", "vendor.fortec-agentguard.testnet", 0.5, "EXECUTE",
               tx_hash="abc123")
    rows = log.recent()
    assert len(rows) == 1
    assert rows[0]["tx_hash"] == "abc123"
    assert rows[0]["explorer_url"].endswith("abc123")
    log.close()


def test_approval_queue_lifecycle(tmp_path):
    log = AuditLog(tmp_path / "a.db")
    ap_id = log.queue_approval("vendor.fortec-agentguard.testnet", 1.5, "over threshold")
    assert len(log.pending_approvals()) == 1
    log.set_approval(ap_id, "executed", "hash999")
    assert log.pending_approvals() == []
    ap = log.get_approval(ap_id)
    assert ap["status"] == "executed"
    assert ap["tx_hash"] == "hash999"
    log.close()


def test_recent_count_velocity_window(tmp_path):
    log = AuditLog(tmp_path / "a.db")
    assert log.recent_count(60) == 0
    log.record("agent", "v", 0.2, "EXECUTE")
    log.record("agent", "v", 0.2, "EXECUTE")
    log.record("agent", "v", 0.2, "BLOCK")  # blocked attempts do not count
    assert log.recent_count(60) == 2
    log.close()
