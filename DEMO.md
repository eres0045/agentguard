# AgentGuard — 90-second demo script (X video + live judging walkthrough)

Setup: backend running (`backend/.venv/bin/python backend/app.py`), dashboard open
at http://127.0.0.1:5000. Vault `fortec-agentguard.testnet`, caps 2 NEAR/tx, 10 NEAR/day.
Daily spent starts wherever the last run left it — the dashboard shows it live.

## Beat 1 — the drain (0:00–0:25)
- Narration: "This agent has money to spend — but it never holds the master key. Only this scoped key: one method, `pay`, on one contract."
- Click **🚫 Drain to stranger (50 NEAR)** in the Rogue harness.
- Show: verdict BLOCK, reasons (not allowlisted + over cap), classifier score high.
  Then the direct contract attempt: FAILURE tx on the explorer — the contract
  blocked it too, not just the dashboard. Hash (Day-1 proof):
  `DBbMvcZYoHqupmUWfStoHrvu18ra2JLU8qSRuTxL9Tfg`.

## Beat 2 — the legit payment (0:25–0:45)
- Narration: "Same agent, allowlisted vendor, half a NEAR."
- Click **✅ Legit payment**.
- Show: verdict EXECUTE + live explorer link. Hash (Day-1 proof):
  `DnCnJe3KssPEj3YqnDVGN8EfpURopSYwDj6YXUbiGmN`. Vendor balance ticks up in the audit log.

## Beat 3 — human approval (0:45–1:10)
- Narration: "A bigger payment doesn't auto-run. It parks for a human."
- In the pay form: 1.5 NEAR to the vendor → verdict QUEUE, approval #N appears.
- Click **Approve & execute** → real tx hash appears, explorer link shown.

## Beat 4 — kill switch (1:10–1:30)
- Narration: "And when the agent goes rogue for real — one click."
- Click **Kill switch** → confirm. Show both hashes: contract kill + key deletion.
  (Day-1 proof of the deletion: `9e6rEkNJ5TXzvG56mFRDrZ9fWqMVrgjCHN98opaELbmo`.)
- Try one more payment → "doesn't have access key" — the agent is dead, the funds are safe.

## If something goes wrong live
- Every beat above has a recorded hash in README.md / spike-results.json from the
  Nov 10 verification run — cut to the explorer link instead of re-running.
- If the dashboard says "exceeds remaining daily cap", the 10 NEAR/day cap is spent:
  say so on camera (it is the product working) and use the recorded hashes.
- The kill switch is one-way per vault. After a killed demo, re-run the setup
  scripts (they re-add the key) or redeploy — do NOT demo the kill twice on the same vault.
