// Step 2 of the Day-1 spike: create the agent sub-account
// `agent.fortec-agentguard.testnet` (funded 1 NEAR from the master) and
// generate the agent's function-call keypair (public key to be added to the
// vault account once the contract is deployed — restricted to `pay` only).
// Usage: node scripts/create-agent.js
const fs = require('fs');
const path = require('path');
const { KeyPair, keyStores, connect, utils } = require('near-api-js');

const RPC_URL = 'https://rpc.testnet.near.org';

async function main() {
  const master = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'keys', 'master.json'), 'utf8'));
  const masterId = master.account_id;
  const agentId = `agent.${masterId}`;
  const keysDir = path.join(__dirname, '..', 'keys');
  const agentPath = path.join(keysDir, 'agent.json');
  const fnCallPath = path.join(keysDir, 'agent-function-call.json');

  const masterKey = KeyPair.fromString(master.secret_key);
  const keyStore = new keyStores.InMemoryKeyStore();
  await keyStore.setKey('testnet', masterId, masterKey);
  const near = await connect({ networkId: 'testnet', keyStore, nodeUrl: RPC_URL });
  const masterAccount = await near.account(masterId);

  // Agent identity keypair (full access to the SUB-account only).
  let agentKey;
  if (fs.existsSync(agentPath)) {
    const saved = JSON.parse(fs.readFileSync(agentPath, 'utf8'));
    if (saved.account_id === agentId) {
      agentKey = KeyPair.fromString(saved.secret_key);
      console.log(`Reusing existing agent identity key for ${agentId}`);
    }
  }
  if (!agentKey) {
    agentKey = KeyPair.fromRandom('ed25519');
    fs.writeFileSync(agentPath, JSON.stringify({
      account_id: agentId,
      public_key: agentKey.getPublicKey().toString(),
      secret_key: agentKey.toString(),
    }, null, 2), { mode: 0o600 });
  }

  // Function-call keypair: this is the ONLY key the agent uses to spend.
  let fnKey;
  if (fs.existsSync(fnCallPath)) {
    const saved = JSON.parse(fs.readFileSync(fnCallPath, 'utf8'));
    fnKey = KeyPair.fromString(saved.secret_key);
    console.log('Reusing existing agent function-call keypair');
  } else {
    fnKey = KeyPair.fromRandom('ed25519');
    fs.writeFileSync(fnCallPath, JSON.stringify({
      note: 'Function-call key ONLY. To be added to the vault account restricted to method pay.',
      public_key: fnKey.getPublicKey().toString(),
      secret_key: fnKey.toString(),
    }, null, 2), { mode: 0o600 });
  }
  console.log(`Agent identity public key: ${agentKey.getPublicKey().toString()}`);
  console.log(`Agent function-call public key: ${fnKey.getPublicKey().toString()}`);

  // Create the sub-account (skip if it already exists).
  try {
    await masterAccount.createAccount(
      agentId,
      agentKey.getPublicKey(),
      utils.format.parseNearAmount('1'),
    );
    console.log(`CREATED sub-account ${agentId} funded with 1 NEAR`);
  } catch (e) {
    const msg = String(e && e.message || e);
    if (msg.includes('already exists') || msg.includes('is already')) {
      console.log(`Sub-account ${agentId} already exists — continuing`);
    } else {
      throw e;
    }
  }

  const agentAccount = await near.account(agentId);
  const state = await agentAccount.state();
  console.log(`VERIFIED: ${agentId} balance ${(Number(state.amount) / 1e24).toFixed(4)} NEAR`);
}

main().catch((e) => { console.error('FAILED:', e.message); process.exit(1); });
