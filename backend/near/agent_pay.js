// Agent payment helper — the ONLY way the agent spends.
// Signs with the agent's FUNCTION-CALL key only (keys/agent-function-call.json).
// That key can call exactly one method (`pay`) on exactly one contract
// (the vault = fortec-agentguard.testnet). It cannot move funds by itself,
// call admin methods, or touch the master key.
// Usage: node agent_pay.js <recipient> <amount_near>
// Prints one JSON object: {ok, tx_hash, explorer, status} or {ok:false, error, tx_hash?}
const fs = require('fs');
const path = require('path');
const { KeyPair, keyStores, connect, utils } = require('near-api-js');

const RPC_URL = 'https://rpc.testnet.near.org';
const EXPLORER = 'https://explorer.testnet.near.org/transactions/';
const GAS = BigInt('100000000000000'); // 100 TGas

async function main() {
  const [recipient, amountNear] = process.argv.slice(2);
  if (!recipient || !amountNear) {
    console.log(JSON.stringify({ ok: false, error: 'usage: node agent_pay.js <recipient> <amount_near>' }));
    process.exit(1);
  }
  const keysDir = path.join(__dirname, '..', '..', 'keys');
  const master = JSON.parse(fs.readFileSync(path.join(keysDir, 'master.json'), 'utf8'));
  const fnKeySaved = JSON.parse(fs.readFileSync(path.join(keysDir, 'agent-function-call.json'), 'utf8'));
  const vaultId = master.account_id;
  const fnKey = KeyPair.fromString(fnKeySaved.secret_key);
  const keyStore = new keyStores.InMemoryKeyStore();
  await keyStore.setKey('testnet', vaultId, fnKey);
  const near = await connect({ networkId: 'testnet', keyStore, nodeUrl: RPC_URL });
  const agent = await near.account(vaultId);
  try {
    const outcome = await agent.functionCall({
      contractId: vaultId, methodName: 'pay',
      args: { recipient, amount: utils.format.parseNearAmount(amountNear) },
      gas: GAS, attachedDeposit: BigInt(0),
    });
    console.log(JSON.stringify({
      ok: true,
      tx_hash: outcome.transaction.hash,
      explorer: EXPLORER + outcome.transaction.hash,
      status: outcome.status,
      recipient, amount_near: amountNear,
    }));
  } catch (e) {
    const msg = String(e && e.message || e);
    const m = msg.match(/([A-Za-z0-9]{43,44})/);
    console.log(JSON.stringify({
      ok: false, error: msg.slice(0, 500),
      tx_hash: m ? m[1] : null,
      explorer: m ? EXPLORER + m[1] : null,
      recipient, amount_near: amountNear,
    }));
    process.exit(2);
  }
}

main().catch((e) => {
  console.log(JSON.stringify({ ok: false, error: String(e && e.message || e).slice(0, 500) }));
  process.exit(1);
});
