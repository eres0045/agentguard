# AgentGuard — pre-submit checkpoint (Day 4, 2026-11-10)

**Status: everything finishable without Ronit is DONE except the hosted demo,
which needs one human gate (a free Hugging Face account). Nothing is submitted.
Deadline: Nov 15, 05:29 IST. Judging Nov 16–18; demo must stay up to Nov 25.**

## 1. Payout address — DONE (no longer a human gate)
Mainnet implicit payout account (free keypair, no purchase/card/crypto):
**`97e837cd7806b7a7a78feac52b1bda9bf2a1f1d5c0143aabd4741602852182a0`**
- Public key: `ed25519:BDywMUJmbuyMmpDCvjBpJj1xbHZrRBhbbk9rdoTG6MwV`
- Private key: ONLY in `keys/mainnet-payout.json` (mode 600, git-ignored —
  verified: `git check-ignore` matches `.gitignore:2:keys/`; `git status`
  shows no keys). Never paste the private key anywhere.
- This is a MAINNET address for the prize-payout field only. The project
  itself is testnet-only; no testnet funds ever go here.

## 2. What is already done (verified)
- [x] Rust vault contract live on testnet (`fortec-agentguard.testnet`);
  caps 2/10 NEAR, allowlist, kill switch; 20/20 unit tests (parent re-verified).
- [x] Flask policy engine + TF classifier + React dashboard; 7 live testnet
  tests with real hashes (README table).
- [x] **Vault top-up (Day 4 fix).** The vault had fallen to 1.88 NEAR
  against a 1.74 NEAR storage floor (173 KB contract) — only 0.14 NEAR of
  spendable headroom, so legit pays failed with "wouldn't have enough
  balance to cover storage". Topped up +4 NEAR from a fresh faucet-funded
  account (`fortec-topup-28982.testnet`, key in goal `hidden_files/
  topup-account.json`, ~6 NEAR spare for future top-ups). Top-up tx:
  `CSMoAitZde5MphWV2dAzsxR2rXTBEBz8Wcg3M6xSYJDf`. Vault balance now
  ~5.88 NEAR → ~4.14 NEAR above the floor. (The vendor's 7.1 NEAR cannot
  be moved back — its key was random and never saved. That is fine.)
- [x] **Demo video, draft (beats 1–3, NO kill switch).**
  `agentguard-demo-draft-2026-11-10.mp4` — **90.0 s, H.264, 1.4 MB**,
  finalized and playable (ffprobe duration 90.000; frames at 20/42/88 s
  read and confirmed). WebM master (94.08 s) alongside it. Both in the
  project dir, git-ignored (`*.webm`, `*.mp4` added to `.gitignore`).
  On-chain proof of this exact take (all three beats executed live):
  - Drain 50 NEAR → BLOCK (policy; audit #48, 11:28:14 IST)
  - Legit 0.5 NEAR → EXECUTE `827VW7QDMu97xT7HnHxTE9W4cHesK1tZAFNd88YJv9P3`
  - 1.5 NEAR → QUEUE (#5) → human-approved → EXECUTE
    `CQJrwWWNYMfrKZpNXApc4LqhvrhaWjLQacNmUf6bjAxQ`
  - Daily spent after the take: **9.5/10 NEAR** (0.5 left today; resets
    00:00 UTC = 05:30 IST Nov 11).
  - **Quality caveat (honest):** the rogue verdicts and tx hashes render
    BELOW the fold at 1280×800 and this take never scrolls to them, so a
    viewer sees the dashboard and the QUEUE card but not the BLOCK/EXECUTE
    text or hashes on screen. The take proves the pipeline works; the
    FINAL take (after the cap reset) must scroll each verdict into view.
- [x] Repo is submission-ready: public-ready README ("do X — see Y"),
  no secrets in git (`git status`: only `.gitignore`, `Dockerfile`,
  `docker-entrypoint.sh`, `.dockerignore`, 2 one-line JS edits),
  **no Intents claims anywhere** (only the honest "no Intents testnet
  exists" note), `keys/` git-ignored and verified.
- [x] HF Spaces deploy pack ready: `Dockerfile`, `docker-entrypoint.sh`,
  `.dockerignore`, `hidden_files/hf-spaces-deploy.md` (steps),
  `hidden_files/hf-deploy.sh` (dry-run tested; refuses to copy `keys/`).
- [x] **Demo video, FINAL (take 2, Nov 11).**
  `agentguard-demo-final-2026-11-11.mp4` — **83.4 s, H.264, 1280×800,
  1.5 MB** (ffprobe-verified; raw 155 s master kept as
  `agentguard-demo-final-2026-11-11-raw.mp4`, edit only trims waiting
  time — every beat is genuine footage). All 4 beats, every verdict and
  tx hash verified visible on screen by frame inspection:
  - Drain 50 NEAR → BLOCK (policy + contract FAILURE, WASM trap)
  - Legit 0.5 NEAR → EXECUTE `DKCYwb2bxmJhpsZGC5rn7gGFg68m4bJeeAfZKKgyubah`
  - 1.5 NEAR → QUEUE (#7) → human-approved → EXECUTE
    `ELT3W7FrJm1aReuZWRJGjraCAB6Z8fufUuZDLBjJhM97`
  - Kill switch → contract kill
    `Ex3CnDKw2b5Awi3E6AveAmghNqp3oU6V64Dyx75vYUQB` + key deletion
    `7HFn4YttRRXs5QdNTc7vjEYdLGCBuaKa13S4ypoZGF4n`; post-kill attempt
    rejected ("vault is killed" / "no matching key pair").
  Take 1 (same day) is SUPERSEDED: its kill-hashes frame never showed on
  screen (scroll targeted a page-level ancestor div). Script fixed in
  `hidden_files/record-final-take.py` (deepest-div / first-row scroll).
- [x] **Vault revived after the final take (Nov 11).** The vault is LIVE
  again for judges: killed=false, caps 2/10 NEAR, daily spent 0/10,
  balance 8.27 NEAR (floor 1.74). Revive tx
  `D7dhG7296r1rDpBQha62yE6XEfyTPCnuVRXkr19rcANq`, agent key re-added
  `9voyM1Gzv7GB9acRfCvokcB9PbSYBTdMm4z3SwQzPvaF`. Liveness re-verified
  after revive via a drain attempt (policy BLOCK + contract FAILURE, no
  funds moved). Top-up +4 NEAR
  `HCeTqUhQYXeC198qTUhrLt4WoqQyDU1vCDKNhf8zZawM` (helper
  fortec-topup-29732.testnet, ~6 NEAR spare).
- [x] Kill switch NOT pressed on the CURRENT vault (revived after take 2).

## 3. Hosted demo — NOT LIVE YET (one human gate)
**There is no public demo URL yet.** Everything hostable from this VM was
tried and is documented in `hidden_files/hf-spaces-deploy.md`:
- Render: 402, card required (proven Nov 8 — do not retry).
- Netlify Functions: cannot carry TF + node + SQLite.
- Cloudflare quick tunnel: blocked by VM egress (QUIC/UDP not permitted;
  HTTP/2 TLS handshake to the edge times out through the proxy). 4 attempts.
- **Route: Hugging Face Spaces (Docker, free, no card). Needs a free HF
  account — none exists for Ronit.** Steps are in
  `hidden_files/hf-spaces-deploy.md` (~15 min: join → new Space `agentguard`
  (Docker, CPU basic, Public) → 3 secrets from `keys/*.json` → run
  `hf-deploy.sh <space-url> --push` → verify). The Space URL then becomes
  the submission demo link. Keep it up to Nov 25.

## 4. Ronit's checkpoint checklist (only human gates left)
1. **Hugging Face account + Space deploy** (see §3) — OR say the word and
   the parent agent does it in the live browser.
2. **X demo post** (Muse has no X access): post the 90 s draft video (or the
   final take, see 5) as a public post stating it was built at NEAR
   HACKATHON, tagging `@NEARProtocol` + `#NEARHackathon`, with the demo
   link once §3 is live. Copy the post URL for the form.
3. **Public GitHub repo**: create `eres0045/agentguard` (public) and push
   this dir (no `keys/`, no videos — both ignored). The submission form
   needs the public repo link.
4. **Go-ahead to submit** — then the form is filled with:
   - Name: `AgentGuard` · Lead: Ronit Shrimankar · Team size: 1 (solo)
   - Tracks: AI Security & Defense (+ Agent Economy, Autonomous Business)
   - Wallet: `97e837cd7806b7a7a78feac52b1bda9bf2a1f1d5c0143aabd4741602852182a0`
   - Repo: (from 3) · Demo post: (from 2) · Email: 007
5. **Optional — final video take (recommended, after 05:30 IST Nov 11):**
   re-record with scrolling (verdicts into view) + the kill-switch beat.
   The kill is one-way per vault: after the final take, redeploy the vault
   (`scripts/deploy-vault.js` re-inits + re-adds the key) so the hosted demo
   stays live for judges. Do NOT press kill before this take.

## 5. Submission form — fields ready
From `hidden_files/near-submission-gates-2026-11-10.md`: public form at
https://nearhackathon.com/#apply (no sign-in). No edit after submit
(corrections only via /request-changes; re-submit of the same repo = 409).
214 submissions in as of Nov 10. Description (20–2,000 chars) — draft:
"AgentGuard is a scoped-key vault that lets an AI agent spend testnet NEAR
without ever holding the master key: per-tx/daily caps, recipient allowlist,
human-approval queue and a kill switch, enforced on-chain by a Rust vault
contract and pre-screened by a Flask policy engine + TensorFlow classifier.
Every decision and tx hash lands in an auditable log. Demo: a rogue agent's
50 NEAR drain is blocked by policy and by the contract, a 0.5 NEAR vendor
payment executes through the agent's function-call key only, a 1.5 NEAR
payment parks for human approval, and the kill switch deletes the agent's
key on-chain."

## 6. Day 5 — final take (2026-11-11, after the 05:30 IST cap reset)

**CORRECTION — the "redeploy the vault" note in §2/§4 was wrong.**
`scripts/deploy-vault.js` re-runs `new`, but near-sdk `#[init]` panics
on an already-initialized account, so redeploy + `new` traps with an
unreachable opcode (proven 2026-11-11: deploy tx
`AJskJLAcXJmTssTFDzVevf4Ej21xN8FbjYNu2XYpxbqq` succeeded, init
failed, vault stayed killed). The working restore is the owner-only
`revive()` added to the contract the same day (un-freezes + resets the
daily window; does NOT re-add the agent key — that is a separate owner
step, `admin.js readd_agent_key`). Kill stays one-way for the AGENT;
only the owner (master key) can revive. The contract was rebuilt
(cargo 1.99, wasm 173,320 bytes) and deployed
(`D3SgCVwS9dpBGujyZY1RnXBUA93G42jF9cPzCyMKQpys`); `admin.js` gained a
`revive` action. Full procedure: deploy wasm → `revive` → `readd_agent_key`
→ verify `policy` (killed=false, spent 0) → top up if balance < ~5 NEAR.

**Cap-reset gotcha (also found Nov 11).** The contract's daily rollover
is lazy and only persists on a SUCCESSFUL `pay` — the Flask policy
engine reads the stored spent (10/10) and BLOCKs everything, so no pay
can reach the chain to trigger the rollover (deadlock). A blocked direct
attempt does not help: `pay` asserts allowlist/cap BEFORE rollover and
a failed tx rolls its state change back. Fix used: one direct agent-key
pay of 0.5 NEAR to the vendor (bypasses the Flask engine)
`GMxC7XJQaWNr1UaGyrAYsgxbmsAsBe9ozHAd2px4PrA7` — day rolled to 20768,
spent 0.5/10, dashboard worked after that. (Take 1 failed on this
before the fix: legit 0.5 BLOCKed "0.0000 NEAR left", no spend made.)

**Take 1 (superseded, 165 s raw).** Beat 1 OK; beat 2 BLOCKed by the
cap deadlock above (audit #54). No kill was pressed. Video deleted.

**Take 2 (FINAL, 83.4 s edited / 155 s raw).** Hashes in §2 above.
Daily spend after take 2: 2.0/10 (counter reset to 0 by the revive).
Vault balance after revive + top-up: 8.27 NEAR.

## 7. Hosted demo — STILL NOT LIVE (no change Nov 11)

HF Space was NOT deployed: the HF account (Eres0007) exists, but
Docker Spaces are PRO-gated and no Space was ever created; nothing was
paid for. Round-2 alternatives
(`hidden_files/hosted-demo-alternatives-round2-2026-11-10.md`) recommend
the **Railway trial** (top pick, $5 one-time grant, no card) — first step
is Ronit's: sign up at railway.com and connect GitHub `eres0045`.
Fallbacks: Replit → SnapDeploy → submit without a hosted demo (the form
needs only the public repo + the X post; a hosted demo is NOT a
submission requirement). The vault itself is live and ready at
fortec-agentguard.testnet whenever a host is chosen; the local dashboard
runs at http://127.0.0.1:5000.
