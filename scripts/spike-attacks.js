// Day-1 spike, part 2 — attack + revocation proofs (all through the agent's
// scoped function-call key; every attempt must FAIL and leave state unchanged):
//   1. over-cap pay: 2 NEAR to vendor (cap is 1 NEAR)
//   2. drain: 50 NEAR to a non-allowlisted address
//   3. privilege escalation: agent calls owner-only `kill` with its pay-only key
//   4. kill switch: master deletes the agent's function-call key on-chain,
//      then the agent's next pay fails (key not found)
//   5. TEST-ENV RESET (not part of the product): re-add the same key so
//      Days 2-4 development can continue. The revocation proof above stands.
// Usage: node scripts/spike-attacks.js
// Appends results to spike-results.json.
const fs = require('fs');
const path = require('path');
const { KeyPair, keyStores, connect, utils } = require('near-api-js');

const RPC_URL = 'https://rpc.testnet.near.org';
const EXPLORER = 'https://explorer.testnet.near.org/transactions/';
const GAS = BigInt('100000000000000');
const NEAR = (n) => utils.format.parseNearAmount(String(n));

async function main() {
  const root = path.join(__dirname, '..');
  const keysDir = path.join(root, 'keys');
  const results = JSON.parse(fs.readFileSync(path.join(root, 'spike-results.json'), 'utf8'));
  const master = JSON.parse(fs.readFileSync(path.join(keysDir, 'master.json'), 'utf8'));
  const fnKeySaved = JSON.parse(fs.readFileSync(path.join(keysDir, 'agent-function-call.json'), 'utf8'));
  const masterId = master.account_id;
  const vendorId = `vendor.${masterId}`;
  const attackerId = 'attacker.evil.testnet';
  const fnPub = fnKeySaved.public_key;

  const log = (step, data) => {
    results.steps.push({ step, ...data });
    console.log(`\n== ${step} ==`);
    console.log(JSON.stringify(data, null, 2));
  };

  const masterKey = KeyPair.fromString(master.secret_key);
  const fnKey = KeyPair.fromString(fnKeySaved.secret_key);
  const keyStore = new keyStores.InMemoryKeyStore();
  await keyStore.setKey('testnet', masterId, masterKey);
  const near = await connect({ networkId: 'testnet', keyStore, nodeUrl: RPC_URL });
  const masterAccount = await near.account(masterId);

  const agentKeyStore = new keyStores.InMemoryKeyStore();
  await agentKeyStore.setKey('testnet', masterId, fnKey);
  const agentNear = await connect({ networkId: 'testnet', keyStore: agentKeyStore, nodeUrl: RPC_URL });
  const agent = await agentNear.account(masterId);

  const stateBefore = async () => {
    const policy = await masterAccount.viewFunction({ contractId: masterId, methodName: 'get_policy', args: {} });
    const vendor = await near.account(vendorId);
    const vs = await vendor.state();
    return { daily_spent_near: Number(policy.daily_spent) / 1e24, vendor_balance_near: Number(vs.amount) / 1e24 };
  };

  // Helper: attempt an agent call; record failure text + hash if extractable.
  async function attemptAgentCall(label, fn) {
    const before = await stateBefore();
    try {
      const outcome = await fn();
      const hash = outcome.transaction ? outcome.transaction.hash : null;
      log(label, { UNEXPECTED: 'call SUCCEEDED — policy did NOT block it', tx_hash: hash, before });
      return { blocked: false, hash };
    } catch (e) {
      const msg = String(e && e.message || e);
      // near-api-js failure errors embed the tx hash in the message in most cases.
      const m = msg.match(/([A-Za-z0-9]{43,44})/);
      const after = await stateBefore();
      log(label, {
        blocked: true,
        error: msg.slice(0, 400),
        tx_hash: m ? m[1] : null,
        explorer: m ? EXPLORER + m[1] : null,
        state_before: before, state_after: after,
        state_unchanged: JSON.stringify(before) === JSON.stringify(after),
      });
      return { blocked: true };
    }
  }

  await attemptAgentCall('attack_over_cap_pay', () =>
    agent.functionCall({ contractId: masterId, methodName: 'pay', args: { recipient: vendorId, amount: NEAR('2') }, gas: GAS, attachedDeposit: BigInt(0) }));
  await attemptAgentCall('attack_drain_non_allowlisted', () =>
    agent.functionCall({ contractId: masterId, methodName: 'pay', args: { recipient: attackerId, amount: NEAR('50') }, gas: GAS, attachedDeposit: BigInt(0) }));
  await attemptAgentCall('attack_privilege_escalation_kill', () =>
    agent.functionCall({ contractId: masterId, methodName: 'kill', args: {}, gas: GAS, attachedDeposit: BigInt(0) }));

  // Kill switch: master deletes the agent's function-call key on-chain.
  const delTx = await masterAccount.deleteKey(fnKey.getPublicKey());
  log('kill_switch_delete_agent_key', {
    tx_hash: delTx.transaction.hash,
    explorer: EXPLORER + delTx.transaction.hash,
    deleted_public_key: fnPub,
  });
  const keysAfter = await masterAccount.getAccessKeys();
  const stillThere = keysAfter.some((k) => k.public_key === fnPub);
  log('verify_key_deleted', { agent_key_still_listed: stillThere, total_keys_on_vault: keysAfter.length });

  await attemptAgentCall('attack_pay_after_revocation', () =>
    agent.functionCall({ contractId: masterId, methodName: 'pay', args: { recipient: vendorId, amount: NEAR('0.5') }, gas: GAS, attachedDeposit: BigInt(0) }));

  // TEST-ENV RESET: re-add the same function-call key for Days 2-4 dev.
  const reAddTx = await masterAccount.addKey(fnKey.getPublicKey(), masterId, ['pay'], NEAR('0.25'));
  log('test_env_reset_readd_agent_key', {
    tx_hash: reAddTx.transaction.hash,
    explorer: EXPLORER + reAddTx.transaction.hash,
    note: 'Dev-only reset so Days 2-4 can continue. The revocation proof above (kill_switch_delete_agent_key + attack_pay_after_revocation) is the real kill-switch evidence; the product demo will end with the key deleted, not re-added.',
  });

  // Confirm the agent can pay again after reset (0.1 NEAR — small, keeps daily total sane).
  try {
    const ok = await agent.functionCall({ contractId: masterId, methodName: 'pay', args: { recipient: vendorId, amount: NEAR('0.1') }, gas: GAS, attachedDeposit: BigInt(0) });
    log('verify_agent_working_after_reset', { tx_hash: ok.transaction.hash, explorer: EXPLORER + ok.transaction.hash, amount: '0.1 NEAR' });
  } catch (e) {
    log('verify_agent_working_after_reset', { FAILED: String(e.message).slice(0, 300) });
  }

  fs.writeFileSync(path.join(root, 'spike-results.json'), JSON.stringify(results, null, 2));
  console.log('\nATTACK SPIKE COMPLETE — results appended to spike-results.json');
}

main().catch((e) => { console.error('FAILED:', e); process.exit(1); });
