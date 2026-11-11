// Admin helper — master-key actions ONLY (human-gated: allowlist, caps,
// kill). Never used on the agent's spend path.
// Usage: node admin.js <action> [args...]
//   policy                                  -> vault policy (view)
//   balances                                -> vault + vendor + agent balances
//   keys                                    -> access keys on the vault account
//   add_recipient <account>
//   remove_recipient <account>
//   set_caps <per_tx_near> <daily_near>
//   kill_contract                           -> contract kill() (one-way freeze)
//   revive                                  -> contract revive() (owner-only restore after a demo kill; does NOT re-add the agent key)
//   delete_agent_key                        -> DeleteKey for the agent fn key
//   readd_agent_key                         -> re-add agent fn key (pay only, 0.25 NEAR)
// Prints one JSON object.
const fs = require('fs');
const path = require('path');
const { KeyPair, keyStores, connect, utils } = require('near-api-js');

const RPC_URL = 'https://rpc.testnet.near.org';
const EXPLORER = 'https://explorer.testnet.near.org/transactions/';
const GAS = BigInt('100000000000000');
const NEAR = (n) => utils.format.parseNearAmount(String(n));

async function main() {
  const [action, ...args] = process.argv.slice(2);
  const keysDir = process.env.AGENTGUARD_KEYS_DIR || path.join(__dirname, '..', '..', 'keys');
  const master = JSON.parse(fs.readFileSync(path.join(keysDir, 'master.json'), 'utf8'));
  const fnKeySaved = JSON.parse(fs.readFileSync(path.join(keysDir, 'agent-function-call.json'), 'utf8'));
  const vaultId = master.account_id;
  const vendorId = `vendor.${vaultId}`;
  const agentId = `agent.${vaultId}`;

  const masterKey = KeyPair.fromString(master.secret_key);
  const keyStore = new keyStores.InMemoryKeyStore();
  await keyStore.setKey('testnet', vaultId, masterKey);
  const near = await connect({ networkId: 'testnet', keyStore, nodeUrl: RPC_URL });
  const masterAccount = await near.account(vaultId);
  const out = (obj) => console.log(JSON.stringify(obj));

  const withHash = (label, outcome) => ({ ok: true, action: label, tx_hash: outcome.transaction.hash, explorer: EXPLORER + outcome.transaction.hash });

  try {
    switch (action) {
      case 'policy': {
        const policy = await masterAccount.viewFunction({ contractId: vaultId, methodName: 'get_policy', args: {} });
        out({ ok: true, action, policy: { ...policy, per_tx_cap_near: Number(policy.per_tx_cap) / 1e24, daily_cap_near: Number(policy.daily_cap) / 1e24, daily_spent_near: Number(policy.daily_spent) / 1e24 } });
        break;
      }
      case 'balances': {
        const bal = async (id) => {
          try { const a = await near.account(id); const s = await a.state(); return Number(s.amount) / 1e24; }
          catch { return null; }
        };
        out({ ok: true, action, vault: vaultId, vault_balance_near: await bal(vaultId), vendor_balance_near: await bal(vendorId), agent_balance_near: await bal(agentId) });
        break;
      }
      case 'keys': {
        const keys = await masterAccount.getAccessKeys();
        out({ ok: true, action, keys: keys.map((k) => ({ public_key: k.public_key, access_key: k.access_key })) });
        break;
      }
      case 'add_recipient': {
        const tx = await masterAccount.functionCall({ contractId: vaultId, methodName: 'add_recipient', args: { account: args[0] }, gas: GAS, attachedDeposit: BigInt(0) });
        out({ ...withHash(action, tx), account: args[0] });
        break;
      }
      case 'remove_recipient': {
        const tx = await masterAccount.functionCall({ contractId: vaultId, methodName: 'remove_recipient', args: { account: args[0] }, gas: GAS, attachedDeposit: BigInt(0) });
        out({ ...withHash(action, tx), account: args[0] });
        break;
      }
      case 'set_caps': {
        const tx = await masterAccount.functionCall({ contractId: vaultId, methodName: 'set_caps', args: { per_tx_cap: NEAR(args[0]), daily_cap: NEAR(args[1]) }, gas: GAS, attachedDeposit: BigInt(0) });
        out({ ...withHash(action, tx), per_tx_cap_near: args[0], daily_cap_near: args[1] });
        break;
      }
      case 'kill_contract': {
        const tx = await masterAccount.functionCall({ contractId: vaultId, methodName: 'kill', args: {}, gas: GAS, attachedDeposit: BigInt(0) });
        out(withHash(action, tx));
        break;
      }
      case 'revive': {
        const tx = await masterAccount.functionCall({ contractId: vaultId, methodName: 'revive', args: {}, gas: GAS, attachedDeposit: BigInt(0) });
        out(withHash(action, tx));
        break;
      }
      case 'delete_agent_key': {
        const tx = await masterAccount.deleteKey(KeyPair.fromString(fnKeySaved.secret_key).getPublicKey());
        out({ ...withHash(action, tx), deleted_public_key: fnKeySaved.public_key });
        break;
      }
      case 'readd_agent_key': {
        const tx = await masterAccount.addKey(KeyPair.fromString(fnKeySaved.secret_key).getPublicKey(), vaultId, ['pay'], NEAR('0.25'));
        out({ ...withHash(action, tx), public_key: fnKeySaved.public_key, methods: ['pay'], allowance: '0.25 NEAR' });
        break;
      }
      default:
        out({ ok: false, error: `unknown action: ${action}` });
        process.exit(1);
    }
  } catch (e) {
    out({ ok: false, action, error: String(e && e.message || e).slice(0, 500) });
    process.exit(2);
  }
}

main().catch((e) => {
  console.log(JSON.stringify({ ok: false, error: String(e && e.message || e).slice(0, 500) }));
  process.exit(1);
});
