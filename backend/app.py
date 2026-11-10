"""AgentGuard backend — Flask API + policy engine + audit log + kill switch.

The backend NEVER holds the master key for spending. Payments are executed
only through the agent's scoped function-call key (backend/near/agent_pay.js).
Master-key actions (allowlist, caps, kill) go through backend/near/admin.js
and are the human-gated endpoints.

Endpoints:
  GET  /api/status      — live on-chain policy + balances + queue depth
  GET  /api/policy      — on-chain policy (caps, spent, allowlist, killed)
  GET  /api/audit       — audit log (newest first)
  GET  /api/approvals   — pending human-approval queue
  POST /api/pay         — {recipient, amount_near, purpose?, actor?}
                           -> EXECUTE (real tx hash) | QUEUE (approval id)
                              | BLOCK (reasons; never touches the chain)
  POST /api/approvals/<id>/approve — human approves -> executes on-chain
  POST /api/approvals/<id>/reject  — human rejects
  POST /api/kill        — kill switch: contract kill() + delete agent key
                           (returns both tx hashes; irreversible)
  POST /api/rogue/<scenario> — rogue harness: legit | overcap | drain | burst
"""
import json
import os
import subprocess
import sys
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

sys.path.insert(0, str(Path(__file__).parent))
from classifier import Classifier  # noqa: E402
from db import AuditLog  # noqa: E402
from policy import PolicyConfig, decide, features  # noqa: E402

ROOT = Path(__file__).parent.parent
NEAR_DIR = Path(__file__).parent / "near"
DB_PATH = ROOT / "data" / "audit.db"
VAULT_ACCOUNT = "fortec-agentguard.testnet"

app = Flask(__name__, static_folder=str(ROOT / "frontend" / "dist"),
            static_url_path="")
audit = AuditLog(DB_PATH)
classifier = None  # lazy: TF import is slow; load on first use


def get_classifier():
    global classifier
    if classifier is None:
        classifier = Classifier()
    return classifier


def run_node(script, *args, timeout=120):
    """Run a NEAR helper; returns parsed JSON stdout."""
    proc = subprocess.run(
        ["node", str(NEAR_DIR / script), *[str(a) for a in args]],
        capture_output=True, text=True, timeout=timeout)
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception:
        return {"ok": False, "error": (proc.stdout + proc.stderr)[-500:]}


def live_policy():
    res = run_node("admin.js", "policy")
    if not res.get("ok"):
        return None, res.get("error", "policy fetch failed")
    p = res["policy"]
    return PolicyConfig(
        per_tx_cap_near=float(p["per_tx_cap_near"]),
        daily_cap_near=float(p["daily_cap_near"]),
        daily_spent_near=float(p["daily_spent_near"]),
        allowlist=set(p["allowlist"]),
        killed=bool(p["killed"]),
    ), None


def execute_payment(recipient, amount_near, actor, purpose=""):
    """Execute via the agent's scoped key; record the outcome."""
    res = run_node("agent_pay.js", recipient, amount_near)
    if res.get("ok"):
        audit.record(actor, recipient, amount_near, "EXECUTE",
                     reasons="executed on-chain via agent scoped key",
                     tx_hash=res["tx_hash"], status=str(res.get("status", "")),
                     purpose=purpose)
        return {"ok": True, "tx_hash": res["tx_hash"], "explorer": res["explorer"]}
    audit.record(actor, recipient, amount_near, "BLOCK",
                 reasons=f"on-chain execution failed: {res.get('error', '')[:200]}",
                 tx_hash=res.get("tx_hash"), purpose=purpose)
    return {"ok": False, "error": res.get("error", "execution failed"),
            "tx_hash": res.get("tx_hash"),
            "explorer": res.get("explorer")}


@app.get("/api/status")
def status():
    cfg, err = live_policy()
    if cfg is None:
        return jsonify({"ok": False, "error": err}), 502
    bals = run_node("admin.js", "balances")
    return jsonify({
        "ok": True,
        "vault": VAULT_ACCOUNT,
        "policy": {"per_tx_cap_near": cfg.per_tx_cap_near,
                   "daily_cap_near": cfg.daily_cap_near,
                   "daily_spent_near": cfg.daily_spent_near,
                   "allowlist": sorted(cfg.allowlist),
                   "killed": cfg.killed},
        "balances": bals if bals.get("ok") else {},
        "pending_approvals": len(audit.pending_approvals()),
    })


@app.get("/api/policy")
def policy():
    cfg, err = live_policy()
    if cfg is None:
        return jsonify({"ok": False, "error": err}), 502
    return jsonify({"ok": True, "per_tx_cap_near": cfg.per_tx_cap_near,
                    "daily_cap_near": cfg.daily_cap_near,
                    "daily_spent_near": cfg.daily_spent_near,
                    "allowlist": sorted(cfg.allowlist), "killed": cfg.killed})


@app.get("/api/audit")
def audit_list():
    return jsonify({"ok": True, "entries": audit.recent(limit=int(request.args.get("limit", 100)))})


@app.get("/api/approvals")
def approvals():
    return jsonify({"ok": True, "pending": audit.pending_approvals()})


@app.post("/api/pay")
def pay():
    body = request.get_json(force=True)
    recipient = str(body.get("recipient", "")).strip()
    purpose = str(body.get("purpose", "")).strip()
    actor = str(body.get("actor", "agent")).strip()
    try:
        amount = float(body.get("amount_near"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "amount_near must be a number"}), 400
    if not recipient:
        return jsonify({"ok": False, "error": "recipient is required"}), 400

    cfg, err = live_policy()
    if cfg is None:
        return jsonify({"ok": False, "error": f"cannot read on-chain policy: {err}"}), 502
    recent = audit.recent_count(60)
    score = get_classifier().score(features(
        amount, recipient in cfg.allowlist, cfg.per_tx_cap_near,
        max(cfg.daily_cap_near - cfg.daily_spent_near, 0.0), recent))
    decision = decide(cfg, recipient, amount, recent, score)

    if decision.verdict == "BLOCK":
        audit.record(actor, recipient, amount, "BLOCK",
                     reasons="; ".join(decision.reasons),
                     classifier_score=score, purpose=purpose)
        return jsonify({"ok": True, "verdict": "BLOCK", **decision.to_dict(),
                        "executed": False})
    if decision.verdict == "QUEUE":
        ap_id = audit.queue_approval(recipient, amount,
                                     reasons="; ".join(decision.reasons),
                                     classifier_score=score, purpose=purpose)
        audit.record(actor, recipient, amount, "QUEUE",
                     reasons="; ".join(decision.reasons),
                     classifier_score=score, purpose=purpose)
        return jsonify({"ok": True, "verdict": "QUEUE", "approval_id": ap_id,
                        **decision.to_dict(), "executed": False})
    result = execute_payment(recipient, amount, actor, purpose)
    if result["ok"]:
        return jsonify({"ok": True, "verdict": "EXECUTE", **decision.to_dict(),
                        "executed": True, "tx_hash": result["tx_hash"],
                        "explorer": result["explorer"]})
    return jsonify({"ok": True, "verdict": "EXECUTE-FAILED", **decision.to_dict(),
                    "executed": False, "error": result["error"],
                    "tx_hash": result.get("tx_hash"),
                    "explorer": result.get("explorer")}), 502


@app.post("/api/approvals/<int:approval_id>/approve")
def approve(approval_id):
    ap = audit.get_approval(approval_id)
    if not ap:
        return jsonify({"ok": False, "error": "approval not found"}), 404
    if ap["status"] != "pending":
        return jsonify({"ok": False, "error": f"already {ap['status']}"}), 409
    cfg, err = live_policy()
    if cfg is None:
        return jsonify({"ok": False, "error": f"cannot read on-chain policy: {err}"}), 502
    if cfg.killed:
        return jsonify({"ok": False, "error": "vault is killed — cannot execute"}), 409
    result = execute_payment(ap["recipient"], ap["amount_near"], "human", ap["purpose"])
    if result["ok"]:
        audit.set_approval(approval_id, "executed", result["tx_hash"])
        audit.record("human", ap["recipient"], ap["amount_near"], "APPROVED",
                     reasons=f"human approved queued payment #{approval_id}",
                     tx_hash=result["tx_hash"], purpose=ap["purpose"])
        return jsonify({"ok": True, "tx_hash": result["tx_hash"],
                        "explorer": result["explorer"]})
    audit.set_approval(approval_id, "approved")
    return jsonify({"ok": False, "error": result["error"],
                    "tx_hash": result.get("tx_hash")}), 502


@app.post("/api/approvals/<int:approval_id>/reject")
def reject(approval_id):
    ap = audit.get_approval(approval_id)
    if not ap:
        return jsonify({"ok": False, "error": "approval not found"}), 404
    if ap["status"] != "pending":
        return jsonify({"ok": False, "error": f"already {ap['status']}"}), 409
    audit.set_approval(approval_id, "rejected")
    audit.record("human", ap["recipient"], ap["amount_near"], "REJECTED",
                 reasons=f"human rejected queued payment #{approval_id}",
                 purpose=ap["purpose"])
    return jsonify({"ok": True, "rejected": approval_id})


@app.post("/api/kill")
def kill():
    """Kill switch (irreversible): freeze the contract, then delete the
    agent's function-call key. Returns both tx hashes."""
    r1 = run_node("admin.js", "kill_contract")
    r2 = run_node("admin.js", "delete_agent_key")
    audit.record("human", VAULT_ACCOUNT, 0, "KILLED",
                 reasons=f"kill switch: contract kill tx {r1.get('tx_hash')}; "
                         f"key deletion tx {r2.get('tx_hash')}")
    return jsonify({"ok": bool(r1.get("ok") and r2.get("ok")),
                    "contract_kill": r1, "key_deletion": r2})


@app.post("/api/rogue/<scenario>")
def rogue(scenario):
    """Run a rogue-harness scenario (legit|overcap|drain|burst|all) and
    return its JSON report. Runs backend/rogue.py as a subprocess."""
    if scenario not in ("legit", "overcap", "drain", "burst", "all"):
        return jsonify({"ok": False, "error": f"unknown scenario {scenario}"}), 400
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "rogue.py"),
         "--base-url", request.host_url.rstrip("/"), "--scenario", scenario],
        capture_output=True, text=True, timeout=300)
    try:
        report = json.loads(proc.stdout)
    except Exception:
        return jsonify({"ok": False, "error": (proc.stdout + proc.stderr)[-500:]}), 502
    return jsonify({"ok": True, "report": report})


@app.get("/")
def index():
    if (ROOT / "frontend" / "dist" / "index.html").exists():
        return send_from_directory(str(ROOT / "frontend" / "dist"), "index.html")
    return jsonify({"ok": True, "service": "agentguard-backend",
                    "note": "frontend not built yet — use the /api/* endpoints"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
