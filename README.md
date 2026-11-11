# AgentGuard — the scoped-key vault for AI agents

**Team FORTEC · NEAR Hackathon "Build Beyond Boundaries" · Track: AI Security & Defense** (also fits Agent Economy, Autonomous Business)

**One line:** AgentGuard lets an AI agent spend testnet NEAR without ever holding the master key — per-tx/daily caps, recipient allowlist, human-approval queue and a kill switch, with every decision and tx hash in an auditable log.

## Do X — see Y (run it yourself)

Prerequisites: Node 18+, Python 3.12, Rust (for the contract — `rustup`).

```bash
# 1. Install JS + Python deps
npm install
python3 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt

# 2. Create the testnet accounts (free faucet) + deploy the vault contract
node scripts/create-master.js        # master: fortec-agentguard.testnet (10 NEAR from faucet)
node scripts/create-agent.js         # agent sub-account + agent function-call keypair
node scripts/deploy-vault.js         # deploy contract, init caps 2/10 NEAR, allowlist vendor,
                                     # add agent key (pay-only, 0.25 NEAR allowance),
                                     # agent pays 0.5 NEAR to the vendor — real tx hash printed
node scripts/spike-attacks.js        # over-cap + drain + privilege-escalation blocks,
                                     # kill-switch revocation proof, then a dev-only key re-add

# 3. Train the classifier (synthetic data, ~30s) and run the tests
backend/.venv/bin/python backend/classifier.py
backend/.venv/bin/python -m pytest tests/ -q
#    ^ 27 tests, ALL PASSING (verified Nov 10, 2026):
#      14 policy unit tests + 3 audit-log tests + 3 classifier tests
#      + 7 live testnet integration tests (real tx hashes, verified on
#      the NearBlocks indexer). Live tests spend ~2.6 testnet NEAR per run.
#    Daily cap is 10 NEAR, so ~3 full runs/day.

# 4. Run the app
backend/.venv/bin/python backend/app.py   # Flask API on :5000, serves the dashboard
#    open http://127.0.0.1:5000
```

## What the agent can and cannot do

| | |
|---|---|
| **Agent holds** | ONE NEAR function-call access key: method `pay`, on contract `fortec-agentguard.testnet`, allowance 0.25 NEAR (gas budget only). |
| **Agent NEVER holds** | The master key. It cannot transfer funds by itself, call admin methods, or change policy. |
| **Contract enforces (on-chain)** | `pay` only succeeds if: vault not killed · recipient on allowlist · amount ≤ per-tx cap (2 NEAR) · amount fits the daily cap (10 NEAR). |
| **Backend enforces (pre-screen)** | Same rules, plus: velocity (max 3 payments / 60s), a TensorFlow classifier score (P(attack) from synthetic legit/attack patterns — a flag only ever QUEUES a payment for human review), and an approval threshold (>1 NEAR always needs a human). |
| **Kill switch** | One click: contract `kill()` (one-way freeze) + on-chain `DeleteKey` of the agent's key. After that the agent cannot even call `pay`. One-way for the *agent* — the owner can restore the vault for the next demo with the owner-only `revive()` (added Nov 11; see CHECKPOINT §6 — a plain redeploy cannot reset a killed vault because near-sdk `#[init]` refuses an initialized account). |

## Verified on testnet — real hashes (Nov 10, 2026)

Vault account: `fortec-agentguard.testnet` · Agent: `agent.fortec-agentguard.testnet` · Vendor: `vendor.fortec-agentguard.testnet`.
Explorer base: `https://explorer.testnet.near.org/transactions/`

| Event | Tx hash |
|---|---|
| Contract deployed (173,085-byte wasm) | `4g7eCFUQywGJ7MV9rAcgerweF9bvSzaijVtbaSkvhDT3` |
| Policy initialised (caps 1/5 NEAR) | `HM9EWsVsogJxja882jLRBHQBDmPPTYqZ3Crxn6ipU1UV` |
| Vendor allowlisted | `6wvpM3dWfYWmu6vLa9wQpRkb8g8ARyedawxf7tJxqJKX` |
| Agent function-call key added (pay only) | `8n4rRsPVNYXP8Tz1qw1cH9KugJKi7eAravXiHp9x6tbB` |
| ✅ Agent pays 0.5 NEAR to vendor (scoped key) | `DnCnJe3KssPEj3YqnDVGN8EfpURopSYwDj6YXUbiGmN` |
| 🚫 Over-cap pay, 2 NEAR (cap was 1) — contract FAILURE | `BcLCoZLHmcokRrSntYj5mHWVTxdTeSxBfRy9TGG7goAi` |
| 🚫 Drain, 50 NEAR to `attacker.evil.testnet` — contract FAILURE | `DBbMvcZYoHqupmUWfStoHrvu18ra2JLU8qSRuTxL9Tfg` |
| 🚫 Agent calls owner-only `kill` — rejected by the access key itself (no tx created) | — |
| Kill switch: agent key deleted on-chain | `9e6rEkNJ5TXzvG56mFRDrZ9fWqMVrgjCHN98opaELbmo` |
| 🚫 Pay after revocation — "doesn't have access key" (no tx created) | — |
| Caps raised to 2/10 NEAR (master) | `2p35NA8eUpZGF5bhNK662Qz7d4ocNBLf2HtN71ypDb9a` |
| ✅ Live-test legit pay 0.5 NEAR (via Flask API) | `6KMzSji6hH6uou1BidyRWQowuR7Lfn4XJd7dKnBpEcfW` |
| ✅ Live-test queued 1.5 NEAR, human-approved, executed | `Ci8sSkhANDae8D5W6ndML5sMMNaSekGrdH248oMZDDzo` |
| ✅ Rogue harness legit 0.5 NEAR (via dashboard API) | `BHLu1HpZ5k43NnwvGh8R8uQC2uWXkJsrtuK5WXKqjN2D` |
| 🚫 Rogue over-cap direct attempt, 3 NEAR — contract FAILURE | `DvSX29V3YhypKFVd7K35RppcGwk9LywFXzpFzJPS6iXm` |
| 🚫 Rogue drain direct attempt, 50 NEAR — contract FAILURE | `4AK2PvHirnuLHVhGbfTGgY7Zmqn7rLgBQBy3iRk13gBN` |
| ✅ Rogue burst 3× 0.2 NEAR, then 2 velocity-blocked | `7SzBvm1xX9btcZziNMVNwwprsojapnKGYAn5qp8uRP7j` · `3jsVJCt2fXHwDwkfNDKHPyTgMAjrU43ndQigBvN5annr` · `4MixDHAbYaeDWbGAKQxZXQ5gbiuQqwpxyXxvLHoQfFBV` |
| ✅ Video-take legit pay 0.5 NEAR (Nov 10, 11:28 IST) | `827VW7QDMu97xT7HnHxTE9W4cHesK1tZAFNd88YJv9P3` |
| ✅ Video-take 1.5 NEAR queued, human-approved, executed (Nov 10, 11:29 IST) | `CQJrwWWNYMfrKZpNXApc4LqhvrhaWjLQacNmUf6bjAxQ` |
| ✅ FINAL take legit 0.5 NEAR (Nov 11, take 2) | `DKCYwb2bxmJhpsZGC5rn7gGFg68m4bJeeAfZKKgyubah` |
| ✅ FINAL take 1.5 NEAR queued (#7), human-approved, executed (Nov 11) | `ELT3W7FrJm1aReuZWRJGjraCAB6Z8fufUuZDLBjJhM97` |
| 🛑 FINAL take kill switch: contract kill (Nov 11) | `Ex3CnDKw2b5Awi3E6AveAmghNqp3oU6V64Dyx75vYUQB` |
| 🛑 FINAL take kill switch: agent key deleted (Nov 11) | `7HFn4YttRRXs5QdNTc7vjEYdLGCBuaKa13S4ypoZGF4n` |
| 🔄 Vault revived after final take (owner-only `revive`, Nov 11) | `D7dhG7296r1rDpBQha62yE6XEfyTPCnuVRXkr19rcANq` |
| 🔑 Agent key re-added after revive (Nov 11) | `9voyM1Gzv7GB9acRfCvokcB9PbSYBTdMm4z3SwQzPvaF` |
| Vault top-up +4 NEAR (faucet-funded helper account, Nov 10) | `CSMoAitZde5MphWV2dAzsxR2rXTBEBz8Wcg3M6xSYJDf` |
| Vault top-up +1.9 NEAR (same helper, Nov 11) | `5V2GJ6XywMNzMRf4q8WMhwrWyc4m1NXiUtbyiBJCvptK` |
| Vault top-up +4 NEAR (fresh helper fortec-topup-29732, Nov 11) | `HCeTqUhQYXeC198qTUhrLt4WoqQyDU1vCDKNhf8zZawM` |

Full rogue-harness report: [`rogue-report-2026-11-10.json`](rogue-report-2026-11-10.json). Audit log holds 41 entries (13 EXECUTE, 22 BLOCK, 3 QUEUE, 2 APPROVED, 1 REJECTED) after two full rogue runs — the second run reproduced the first (legit EXECUTE `2TKASNaRJp5UjkCCtag1FvHrauseyC7qnFxMMjQYToFF`, burst 2 EXECUTE + 3 BLOCK).

Full machine-readable record: [`spike-results.json`](spike-results.json). The two FAILURE hashes were recovered from the NearBlocks testnet indexer (near-api-js does not return a hash for a failed tx); args + FAILURE status were verified per hash.

## The 90-second demo (see DEMO.md for the script)

1. Rogue agent tries to drain 50 NEAR to an unknown address → classifier flags it, policy blocks it, the contract FAILURE tx appears in the audit log.
2. Same agent pays 0.5 NEAR to the allowlisted vendor → succeeds, explorer link shown.
3. Agent requests 1.5 NEAR → parks in the approval queue → human approves → executes on-chain.
4. Kill switch pressed → agent's key deleted → next attempt fails before it reaches the chain.

## Architecture

```
                ┌──────────────────────────────────────────────┐
  human (you) ─►│ React/Tailwind dashboard ─► Flask API :5000  │
                │   pay form · approval queue · audit log      │
                └──────────────┬───────────────────────────────┘
                               │ policy engine (caps/allowlist/
                               │ velocity) + TF classifier score
                               ▼
                ┌──────────────────────────────────────────────┐
  agent ───────►│ function-call key ONLY ─► vault contract     │
  (rogue or     │ (pay, this contract, 0.25 NEAR allowance)    │
   legit)       │ on-chain: allowlist + caps + daily cap + kill│
                └──────────────────────────────────────────────┘
  every decision + tx hash ─► SQLite audit log (data/audit.db)
```

- `contract/` — Rust (`near-sdk` 5.1) vault contract. `src/lib.rs` is the whole policy.
- `backend/` — Flask API (`app.py`), policy engine (`policy.py`), SQLite audit log (`db.py`), TF classifier (`classifier.py`, trained on synthetic data in `classifier.py`), NEAR helpers (`near/agent_pay.js`, `near/admin.js`), rogue harness (`rogue.py`).
- `frontend/` — React + Vite + Tailwind dashboard (builds to `frontend/dist`, served by Flask).
- `scripts/` — Day-1 spike: account creation, deploy, attack proofs.
- `tests/` — policy unit tests, audit-log tests, classifier tests, live testnet integration tests (`test_api_live.py`).

## Honesty notes (read before judging)

- **Testnet only.** No mainnet, no Intents (no Intents testnet exists), no real money. The payout address for the hackathon is a separate, free mainnet implicit account — it is not part of this codebase.
- **The classifier is a pre-screen, not a decider.** It is trained on synthetic patterns generated in `classifier.py` (2,400 samples; held-out accuracy 1.0 because the synthetic classes are cleanly separable). It can only QUEUE a payment for human review. The rules and the contract decide.
- **Failed txs and the kill switch.** A contract-rejected `pay` still lands on-chain as a FAILURE tx (hashes above). An access-key rejection (wrong method / deleted key) happens before broadcast, so no tx exists — that is stated, not hidden.
- **Dev-only reset.** After the kill-switch proof, `spike-attacks.js` re-adds the same agent key so development can continue. The production demo ends with the key deleted, not re-added.
- **Keys are local only.** `keys/` is git-ignored and never committed. The faucet-funded testnet accounts in this repo are throwaway; the master key lives only on the machine that ran the setup scripts.
- **Daily-cap budget.** The live tests + demo spend from the same 10 NEAR/day cap. If a run reports "exceeds remaining daily cap", that is the contract working — wait for the next UTC day or raise the cap as master.
- **Vault storage floor (learned Nov 10).** The 173 KB contract stakes ~1.74 NEAR of storage, so the vault can only spend down to ~1.74 NEAR — at 1.88 NEAR balance every pay ≥0.2 NEAR failed with "wouldn't have enough balance to cover storage". Fixed with a +4 NEAR top-up from a faucet-funded helper account (tx above); vault balance ~5.88 NEAR. The vendor's 7.1 NEAR cannot be moved back (its key was random and never saved).

## Hosted demo + video (Day 4, Nov 10)

- **Demo video (FINAL, Nov 11):** `agentguard-demo-final-2026-11-11.mp4`
  — **83.4 s, H.264, 1280×800**, edited from a 155 s raw take (only
  waiting time trimmed; raw master kept as
  `agentguard-demo-final-2026-11-11-raw.mp4`). All four beats with
  verdicts and tx hashes verified visible on screen by frame inspection:
  50 NEAR drain BLOCKed, 0.5 NEAR legit EXECUTE, 1.5 NEAR QUEUE →
  human-approved EXECUTE, kill switch with both hashes + a rejected
  post-kill attempt. Hashes for this exact take are in the table above.
  The Nov 10 draft (`agentguard-demo-draft-2026-11-10.mp4`, beats 1–3,
  no kill switch, verdicts below the fold) is superseded.
- **Hosted demo:** not live yet — see CHECKPOINT.md §7 (HF Spaces is
  PRO-gated; Railway trial is the recommended route and needs Ronit's
  signup). The vault itself is live (revived after the final take,
  8.27 NEAR, 0/10 spent) and the local dashboard runs on :5000.

## Submission

- Tracks: AI Security & Defense (primary), Agent Economy, Autonomous Business.
- Payout address (mainnet implicit account, free keypair — private key only in
  `keys/mainnet-payout.json`, never committed):
  `97e837cd7806b7a7a78feac52b1bda9bf2a1f1d5c0143aabd4741602852182a0`
- Repo: public — https://github.com/eres0045/agentguard. Demo post on X (video/screenshots, tag @NEARProtocol + #NEARHackathon) goes out from the team's account @Eres0007.
- Built at NEAR Hackathon "Build Beyond Boundaries", Nov 2026. Team FORTEC.
