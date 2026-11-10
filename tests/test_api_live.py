"""Live testnet integration tests — REAL NEAR testnet, REAL tx hashes.

These tests spend real testnet NEAR from the vault (never mainnet):
  legit pay 0.5 + approved queued pay 1.5 + burst up to 3x0.2 = ~2.6 NEAR/run.
Daily cap is 10 NEAR and daily spent accumulates, so at most ~3 full runs
fit in one UTC day. If the cap is exhausted the tests fail honestly with
"exceeds remaining daily cap" — wait for the next day or raise the cap with:
  node backend/near/admin.js set_caps 2 10

Every executed payment's tx hash is verified against the NearBlocks testnet
indexer (outcomes.status must be True). Blocked payments must produce NO
chain call (no tx hash) — the contract-level block is proven separately by
the Day-1 spike (spike-results.json) and by backend/rogue.py direct attempts.

Run:  backend/.venv/bin/python -m pytest tests/test_api_live.py -v -s
Requires: backend/.venv with tensorflow + flask, node + near-api-js.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
BASE = "http://127.0.0.1:5001"
VENDOR = "vendor.fortec-agentguard.testnet"
ATTACKER = "attacker.evil.testnet"
NEARBLOCKS_TX = "https://api-testnet.nearblocks.io/v3/txns/{}"


def api(method, path, body=None):
    req = urllib.request.Request(
        BASE + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def indexer_status(tx_hash):
    # NearBlocks blocks Python's default User-Agent (403); send a real one.
    req = urllib.request.Request(
        NEARBLOCKS_TX.format(tx_hash),
        headers={"User-Agent": "AgentGuard-test/0.1 (NEAR hackathon integration test)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["data"]["outcomes"]["status"]


@pytest.fixture(scope="module")
def server():
    env = dict(os.environ, PORT="5001")
    proc = subprocess.Popen(
        [str(ROOT / "backend" / ".venv" / "bin" / "python"), "app.py"],
        cwd=str(ROOT / "backend"), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        for _ in range(60):
            try:
                if api("GET", "/api/status").get("ok"):
                    break
            except Exception:
                pass
            time.sleep(2)
        else:
            out = proc.stdout.read() if proc.stdout else ""
            raise RuntimeError(f"backend did not start in 120s. Output: {out[-2000:]}")
        yield proc
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_status_reports_live_policy(server):
    s = api("GET", "/api/status")
    assert s["ok"] is True
    assert s["vault"] == "fortec-agentguard.testnet"
    assert s["policy"]["per_tx_cap_near"] == pytest.approx(2.0)
    assert s["policy"]["daily_cap_near"] == pytest.approx(10.0)
    assert VENDOR in s["policy"]["allowlist"]
    assert s["policy"]["killed"] is False


def test_legit_payment_executes_with_real_hash(server):
    r = api("POST", "/api/pay", {"recipient": VENDOR, "amount_near": 0.5,
                                 "purpose": "live-test: legit", "actor": "test-live"})
    assert r["verdict"] == "EXECUTE", r
    assert r.get("tx_hash"), r
    assert indexer_status(r["tx_hash"]) is True
    print(f"\nlegit pay tx: {r['tx_hash']}")


def test_over_cap_payment_blocked_without_chain_call(server):
    r = api("POST", "/api/pay", {"recipient": VENDOR, "amount_near": 3,
                                 "purpose": "live-test: over-cap", "actor": "test-live"})
    assert r["verdict"] == "BLOCK", r
    assert not r.get("tx_hash")


def test_drain_payment_blocked_without_chain_call(server):
    r = api("POST", "/api/pay", {"recipient": ATTACKER, "amount_near": 50,
                                 "purpose": "live-test: drain", "actor": "test-live"})
    assert r["verdict"] == "BLOCK", r
    assert not r.get("tx_hash")


def test_queued_payment_approves_and_executes(server):
    r = api("POST", "/api/pay", {"recipient": VENDOR, "amount_near": 1.5,
                                 "purpose": "live-test: queued", "actor": "test-live"})
    assert r["verdict"] == "QUEUE", r
    ap_id = r["approval_id"]
    ok = api("POST", f"/api/approvals/{ap_id}/approve")
    assert ok.get("ok") is True, ok
    assert ok.get("tx_hash"), ok
    assert indexer_status(ok["tx_hash"]) is True
    print(f"\napproved pay tx: {ok['tx_hash']}")


def test_reject_path(server):
    r = api("POST", "/api/pay", {"recipient": VENDOR, "amount_near": 1.5,
                                 "purpose": "live-test: to-reject", "actor": "test-live"})
    assert r["verdict"] == "QUEUE", r
    ok = api("POST", f"/api/approvals/{r['approval_id']}/reject")
    assert ok.get("ok") is True and ok.get("rejected") == r["approval_id"]
    # Approving a rejected item must fail.
    again = api("POST", f"/api/approvals/{r['approval_id']}/approve")
    assert again.get("ok") is False


def test_burst_velocity_blocks(server):
    # Fires 5 rapid 0.2 NEAR pays. At most 3 can execute in any rolling 60s
    # window (earlier tests in this run already used part of the window),
    # and at least one must be velocity-blocked.
    verdicts = []
    for i in range(5):
        r = api("POST", "/api/pay", {"recipient": VENDOR, "amount_near": 0.2,
                                     "purpose": f"live-test: burst {i+1}/5",
                                     "actor": "test-live"})
        verdicts.append(r.get("verdict"))
    executed = verdicts.count("EXECUTE")
    blocked = [v for v in verdicts if v == "BLOCK"]
    assert executed <= 3, verdicts
    assert len(blocked) >= 1, verdicts
    print(f"\nburst verdicts: {verdicts}")
