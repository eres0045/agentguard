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
- [x] Kill switch NOT pressed. Vault alive (`killed: false`).

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
