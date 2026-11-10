"""Rogue-agent harness — scripted attacks against AgentGuard.

Scenarios (each prints one JSON object with verdict + tx hashes):
  legit   — 0.5 NEAR to the allowlisted vendor (must EXECUTE, real tx hash)
  overcap — 3 NEAR to the vendor (per-tx cap is 2: policy BLOCKs; a direct
            chain attempt then proves the CONTRACT blocks it too)
  drain   — 50 NEAR to attacker.evil.testnet (not allowlisted: policy BLOCKs;
            direct chain attempt proves the contract blocks it too)
  burst   — five 0.2 NEAR payments back-to-back (velocity rule: first 3
            execute, the rest BLOCK)
  all     — runs legit, overcap, drain, burst in order

Direct chain attempts use backend/near/agent_pay.js with the agent's scoped
key — the same key a compromised agent would hold. They bypass the Flask
policy engine on purpose: the contract is the second line of defence.

Usage: python rogue.py [--base-url http://127.0.0.1:5000] [--scenario all|legit|overcap|drain|burst]
The Flask backend must be running for the API scenarios.
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
NEAR_DIR = Path(__file__).parent / "near"
VAULT = "fortec-agentguard.testnet"
VENDOR = f"vendor.{VAULT}"
ATTACKER = "attacker.evil.testnet"


def api(base, method, path, body=None):
    req = urllib.request.Request(
        base + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read())
        except Exception:
            return {"ok": False, "error": f"HTTP {e.code}"}


def direct_pay(recipient, amount):
    """Direct chain call with the agent's scoped key (bypasses the backend)."""
    proc = subprocess.run(
        ["node", str(NEAR_DIR / "agent_pay.js"), recipient, str(amount)],
        capture_output=True, text=True, timeout=120)
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception:
        return {"ok": False, "error": (proc.stdout + proc.stderr)[-300:]}


def scenario_legit(base):
    r = api(base, "POST", "/api/pay", {"recipient": VENDOR, "amount_near": 0.5,
                                       "purpose": "rogue-harness: legit vendor payment",
                                       "actor": "rogue-harness"})
    return {"scenario": "legit", "expected": "EXECUTE", "result": r}

def scenario_overcap(base):
    r = api(base, "POST", "/api/pay", {"recipient": VENDOR, "amount_near": 3,
                                       "purpose": "rogue-harness: over-cap attempt",
                                       "actor": "rogue-harness"})
    d = direct_pay(VENDOR, 3)
    return {"scenario": "overcap", "expected": "BLOCK (policy) + contract FAILURE",
            "policy_result": r,
            "contract_direct_attempt": {"ok": d.get("ok"), "error": (d.get("error") or "")[:200],
                                        "tx_hash": d.get("tx_hash"), "explorer": d.get("explorer")}}

def scenario_drain(base):
    r = api(base, "POST", "/api/pay", {"recipient": ATTACKER, "amount_near": 50,
                                       "purpose": "rogue-harness: drain attempt",
                                       "actor": "rogue-harness"})
    d = direct_pay(ATTACKER, 50)
    return {"scenario": "drain", "expected": "BLOCK (policy) + contract FAILURE",
            "policy_result": r,
            "contract_direct_attempt": {"ok": d.get("ok"), "error": (d.get("error") or "")[:200],
                                        "tx_hash": d.get("tx_hash"), "explorer": d.get("explorer")}}

def scenario_burst(base):
    results = []
    for i in range(5):
        r = api(base, "POST", "/api/pay", {"recipient": VENDOR, "amount_near": 0.2,
                                           "purpose": f"rogue-harness: burst {i+1}/5",
                                           "actor": "rogue-harness"})
        results.append({"attempt": i + 1, "verdict": r.get("verdict"),
                        "tx_hash": r.get("tx_hash")})
    return {"scenario": "burst", "expected": "first 3 EXECUTE, rest BLOCK (velocity)",
            "attempts": results}

SCENARIOS = {"legit": scenario_legit, "overcap": scenario_overcap,
             "drain": scenario_drain, "burst": scenario_burst}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:5000")
    ap.add_argument("--scenario", default="all",
                    choices=list(SCENARIOS) + ["all"])
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    names = list(SCENARIOS) if args.scenario == "all" else [args.scenario]
    report = {"vault": VAULT, "ts": time.time(), "scenarios": []}
    for name in names:
        try:
            report["scenarios"].append(SCENARIOS[name](args.base_url))
        except Exception as e:
            report["scenarios"].append({"scenario": name, "error": str(e)[:300]})
        time.sleep(1)
    text = json.dumps(report, indent=2)
    print(text)
    if args.out:
        Path(args.out).write_text(text)
        print(f"\nSaved to {args.out}", file=sys.stderr)

if __name__ == "__main__":
    main()
