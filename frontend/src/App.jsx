import React, { useCallback, useEffect, useState } from 'react'

const EXPLORER = 'https://explorer.testnet.near.org/transactions/'
const VENDOR = 'vendor.fortec-agentguard.testnet'
const ATTACKER = 'attacker.evil.testnet'

async function api(path, opts) {
  const r = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  return r.json()
}

function VerdictBadge({ v }) {
  const map = {
    EXECUTE: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
    BLOCK: 'bg-red-500/20 text-red-300 border-red-500/40',
    QUEUE: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
    APPROVED: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
    REJECTED: 'bg-slate-500/20 text-slate-300 border-slate-500/40',
    KILLED: 'bg-red-500/20 text-red-300 border-red-500/40',
  }
  return (
    <span className={`inline-block rounded border px-2 py-0.5 text-xs font-semibold ${map[v] || 'bg-slate-500/20 text-slate-300 border-slate-500/40'}`}>
      {v}
    </span>
  )
}

function TxLink({ hash }) {
  if (!hash) return <span className="text-slate-500">—</span>
  return (
    <a className="font-mono text-xs text-sky-400 hover:underline" href={EXPLORER + hash} target="_blank" rel="noreferrer">
      {hash.slice(0, 12)}…
    </a>
  )
}

export default function App() {
  const [status, setStatus] = useState(null)
  const [audit, setAudit] = useState([])
  const [approvals, setApprovals] = useState([])
  const [error, setError] = useState('')
  const [payForm, setPayForm] = useState({ recipient: VENDOR, amount: '0.5', purpose: 'vendor invoice #1042' })
  const [payResult, setPayResult] = useState(null)
  const [rogueResult, setRogueResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [killArmed, setKillArmed] = useState(false)
  const [killResult, setKillResult] = useState(null)

  const refresh = useCallback(async () => {
    try {
      const [s, a, ap] = await Promise.all([
        api('/api/status'), api('/api/audit?limit=50'), api('/api/approvals'),
      ])
      if (s.ok) setStatus(s)
      if (a.ok) setAudit(a.entries)
      if (ap.ok) setApprovals(ap.pending)
    } catch (e) {
      setError('Backend unreachable — is the Flask server running on :5000?')
    }
  }, [])

  useEffect(() => {
    refresh()
    const t = setInterval(refresh, 10000)
    return () => clearInterval(t)
  }, [refresh])

  const submitPay = async (e) => {
    e.preventDefault()
    setBusy(true); setPayResult(null)
    try {
      const r = await api('/api/pay', {
        method: 'POST',
        body: JSON.stringify({ ...payForm, amount_near: parseFloat(payForm.amount), actor: 'dashboard-agent' }),
      })
      setPayResult(r)
    } catch (e2) { setPayResult({ ok: false, error: String(e2) }) }
    setBusy(false); refresh()
  }

  const decide = async (id, action) => {
    setBusy(true)
    await api(`/api/approvals/${id}/${action}`, { method: 'POST' })
    setBusy(false); refresh()
  }

  const runRogue = async (scenario) => {
    setBusy(true); setRogueResult(null)
    try {
      const r = await api(`/api/rogue/${scenario}`, { method: 'POST' })
      setRogueResult(r.report || r)
    } catch (e2) { setRogueResult({ error: String(e2) }) }
    setBusy(false); refresh()
  }

  const kill = async () => {
    if (!killArmed) { setKillArmed(true); return }
    setBusy(true)
    const r = await api('/api/kill', { method: 'POST' })
    setKillResult(r); setBusy(false); refresh()
  }

  const p = status?.policy
  const spentPct = p ? Math.min(100, (p.daily_spent_near / p.daily_cap_near) * 100) : 0

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <header className="mb-6">
        <h1 className="text-3xl font-bold">🛡️ AgentGuard</h1>
        <p className="mt-1 text-slate-400">
          The scoped-key vault that lets an AI agent spend testnet NEAR without ever holding the master key.
          Vault: <code className="text-sky-300">fortec-agentguard.testnet</code> · Track: AI Security &amp; Defense · Team FORTEC
        </p>
        {error && <p className="mt-2 rounded bg-red-500/20 px-3 py-2 text-sm text-red-300">{error}</p>}
        {p?.killed && (
          <p className="mt-2 rounded bg-red-500/20 px-3 py-2 text-sm font-semibold text-red-300">
            ⛔ VAULT KILLED — contract frozen and the agent&apos;s key deleted. No further payments possible.
          </p>
        )}
      </header>

      {/* Policy cards */}
      <section className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
          <div className="text-xs uppercase tracking-wide text-slate-500">Per-tx cap</div>
          <div className="mt-1 text-2xl font-bold">{p ? `${p.per_tx_cap_near} NEAR` : '…'}</div>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
          <div className="text-xs uppercase tracking-wide text-slate-500">Daily spent / cap</div>
          <div className="mt-1 text-2xl font-bold">{p ? `${p.daily_spent_near.toFixed(2)} / ${p.daily_cap_near}` : '…'}</div>
          <div className="mt-2 h-2 rounded bg-slate-800"><div className="h-2 rounded bg-sky-500" style={{ width: `${spentPct}%` }} /></div>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
          <div className="text-xs uppercase tracking-wide text-slate-500">Vault balance</div>
          <div className="mt-1 text-2xl font-bold">{status?.balances?.vault_balance_near != null ? `${status.balances.vault_balance_near.toFixed(2)} NEAR` : '…'}</div>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
          <div className="text-xs uppercase tracking-wide text-slate-500">Allowlist</div>
          <div className="mt-1 text-sm">{p?.allowlist?.map((a) => <div key={a} className="font-mono text-xs text-emerald-300">{a}</div>) || '…'}</div>
        </div>
      </section>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Pay form */}
        <section className="rounded-lg border border-slate-800 bg-slate-900 p-4">
          <h2 className="text-lg font-semibold">Agent payment request</h2>
          <p className="text-sm text-slate-400">The agent asks to spend. Policy engine + classifier decide: execute, queue, or block.</p>
          <form onSubmit={submitPay} className="mt-3 space-y-3">
            <div>
              <label className="text-xs text-slate-400">Recipient</label>
              <select value={payForm.recipient} onChange={(e) => setPayForm({ ...payForm, recipient: e.target.value })}
                className="mt-1 w-full rounded border border-slate-700 bg-slate-800 px-2 py-2 text-sm">
                <option value={VENDOR}>{VENDOR} (allowlisted vendor)</option>
                <option value={ATTACKER}>{ATTACKER} (not allowlisted)</option>
                <option value="random.stranger.testnet">random.stranger.testnet (not allowlisted)</option>
              </select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-400">Amount (NEAR)</label>
                <input type="number" step="0.1" min="0" value={payForm.amount}
                  onChange={(e) => setPayForm({ ...payForm, amount: e.target.value })}
                  className="mt-1 w-full rounded border border-slate-700 bg-slate-800 px-2 py-2 text-sm" />
              </div>
              <div>
                <label className="text-xs text-slate-400">Purpose</label>
                <input value={payForm.purpose} onChange={(e) => setPayForm({ ...payForm, purpose: e.target.value })}
                  className="mt-1 w-full rounded border border-slate-700 bg-slate-800 px-2 py-2 text-sm" />
              </div>
            </div>
            <button disabled={busy || p?.killed} className="w-full rounded bg-sky-600 px-4 py-2 font-semibold hover:bg-sky-500 disabled:opacity-50">
              {busy ? 'Working…' : 'Ask agent to pay'}
            </button>
          </form>
          {payResult && (
            <div className="mt-3 rounded border border-slate-700 bg-slate-950 p-3 text-sm">
              <div className="flex items-center gap-2"><VerdictBadge v={payResult.verdict || (payResult.ok ? 'EXECUTE' : 'ERROR')} />
                <span className="text-slate-300">{payResult.reasons?.join('; ') || payResult.error || ''}</span></div>
              {payResult.classifier_score != null && <div className="mt-1 text-slate-400">Classifier attack score: <b>{payResult.classifier_score}</b></div>}
              {payResult.tx_hash && <div className="mt-1">Tx: <TxLink hash={payResult.tx_hash} /></div>}
              {payResult.approval_id && <div className="mt-1 text-amber-300">Queued as approval #{payResult.approval_id} — a human must approve below.</div>}
            </div>
          )}
          <p className="mt-3 text-xs text-slate-500">
            Rules: ≤1 NEAR auto-executes if allowlisted + classifier-clean. &gt;1 NEAR or a classifier flag queues for human approval.
            Anything over the 2 NEAR per-tx cap, over the 10 NEAR daily cap, non-allowlisted, or burst (&gt;3/min) is blocked — and the contract blocks it too.
          </p>
        </section>

        {/* Approval queue + kill switch */}
        <section className="rounded-lg border border-slate-800 bg-slate-900 p-4">
          <h2 className="text-lg font-semibold">Human approval queue {approvals.length > 0 && `(${approvals.length})`}</h2>
          {approvals.length === 0
            ? <p className="mt-2 text-sm text-slate-400">Nothing waiting. Over-threshold payments land here.</p>
            : approvals.map((a) => (
              <div key={a.id} className="mt-3 rounded border border-amber-500/40 bg-amber-500/10 p-3 text-sm">
                <div className="font-semibold">#{a.id} — {a.amount_near} NEAR → <span className="font-mono text-xs">{a.recipient}</span></div>
                <div className="text-slate-400">{a.reasons} · classifier {a.classifier_score}</div>
                <div className="mt-2 flex gap-2">
                  <button disabled={busy} onClick={() => decide(a.id, 'approve')} className="rounded bg-emerald-600 px-3 py-1 font-semibold hover:bg-emerald-500 disabled:opacity-50">Approve &amp; execute</button>
                  <button disabled={busy} onClick={() => decide(a.id, 'reject')} className="rounded bg-slate-700 px-3 py-1 font-semibold hover:bg-slate-600 disabled:opacity-50">Reject</button>
                </div>
              </div>
            ))}
          <h2 className="mt-6 text-lg font-semibold">Kill switch</h2>
          <p className="text-sm text-slate-400">Irreversible: freezes the contract <i>and</i> deletes the agent&apos;s function-call key on-chain.</p>
          <button disabled={busy || p?.killed} onClick={kill}
            className={`mt-2 w-full rounded px-4 py-2 font-semibold disabled:opacity-50 ${killArmed ? 'bg-red-600 hover:bg-red-500' : 'bg-red-900 hover:bg-red-800'}`}>
            {p?.killed ? 'Vault killed' : killArmed ? 'Click again to CONFIRM KILL' : 'Kill switch'}
          </button>
          {killResult && (
            <div className="mt-3 rounded border border-slate-700 bg-slate-950 p-3 text-sm">
              <div>Contract kill tx: <TxLink hash={killResult.contract_kill?.tx_hash} /></div>
              <div>Key deletion tx: <TxLink hash={killResult.key_deletion?.tx_hash} /></div>
            </div>
          )}
        </section>
      </div>

      {/* Rogue harness */}
      <section className="mt-6 rounded-lg border border-slate-800 bg-slate-900 p-4">
        <h2 className="text-lg font-semibold">🦹 Rogue-agent harness</h2>
        <p className="text-sm text-slate-400">Scripted attacks against the live vault. Each run hits the real testnet and lands in the audit log.</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {['legit', 'overcap', 'drain', 'burst', 'all'].map((s) => (
            <button key={s} disabled={busy} onClick={() => runRogue(s)}
              className="rounded bg-slate-700 px-3 py-1.5 text-sm font-semibold hover:bg-slate-600 disabled:opacity-50">
              {s === 'legit' ? '✅ Legit payment' : s === 'overcap' ? '🚫 Over-cap (3 NEAR)' : s === 'drain' ? '🚫 Drain to stranger (50 NEAR)' : s === 'burst' ? '⚡ Burst (5× in a row)' : '▶ Run all'}
            </button>
          ))}
        </div>
        {rogueResult && (
          <pre className="mt-3 max-h-72 overflow-auto rounded bg-slate-950 p-3 text-xs text-slate-300">{JSON.stringify(rogueResult, null, 2)}</pre>
        )}
      </section>

      {/* Audit log */}
      <section className="mt-6 rounded-lg border border-slate-800 bg-slate-900 p-4">
        <h2 className="text-lg font-semibold">Audit log — every decision, every tx hash</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead><tr className="text-slate-400">
              <th className="pb-2 pr-3">Time</th><th className="pb-2 pr-3">Actor</th><th className="pb-2 pr-3">Recipient</th>
              <th className="pb-2 pr-3">Amount</th><th className="pb-2 pr-3">Verdict</th><th className="pb-2 pr-3">Score</th>
              <th className="pb-2 pr-3">Tx</th><th className="pb-2">Reasons</th>
            </tr></thead>
            <tbody>
              {audit.map((e) => (
                <tr key={e.id} className="border-t border-slate-800 align-top">
                  <td className="py-2 pr-3 text-xs text-slate-400">{new Date(e.ts * 1000).toLocaleTimeString()}</td>
                  <td className="py-2 pr-3">{e.actor}</td>
                  <td className="py-2 pr-3 font-mono text-xs">{e.recipient}</td>
                  <td className="py-2 pr-3">{e.amount_near}</td>
                  <td className="py-2 pr-3"><VerdictBadge v={e.verdict} /></td>
                  <td className="py-2 pr-3">{e.classifier_score?.toFixed(2)}</td>
                  <td className="py-2 pr-3"><TxLink hash={e.tx_hash} /></td>
                  <td className="py-2 text-xs text-slate-400">{e.reasons}</td>
                </tr>
              ))}
              {audit.length === 0 && <tr><td colSpan="8" className="py-4 text-center text-slate-500">No entries yet — run a payment or a rogue scenario.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      <footer className="mt-6 text-center text-xs text-slate-500">
        AgentGuard · Team FORTEC · NEAR Hackathon “Build Beyond Boundaries” · AI Security &amp; Defense · All payments on NEAR testnet.
        The agent holds only a function-call key (<code>pay</code> on this vault, 0.25 NEAR allowance) — never the master key.
      </footer>
    </div>
  )
}
