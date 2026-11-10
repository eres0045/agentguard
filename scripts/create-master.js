// Step 1 of the Day-1 spike: create the master testnet account via the
// official testnet helper (free faucet). Generates a fresh ed25519 keypair,
// asks helper.testnet.near.org to create + fund the account, verifies the
// balance over RPC, and saves the key to keys/master.json (git-ignored).
// Usage: node scripts/create-master.js [account-id]
// Default account: fortec-agentguard.testnet
const fs = require('fs');
const path = require('path');
const { KeyPair, keyStores, connect } = require('near-api-js');

const RPC_URL = 'https://rpc.testnet.near.org';
const HELPER_URL = 'https://helper.testnet.near.org/account';

async function main() {
  const accountId = process.argv[2] || 'fortec-agentguard.testnet';
  const keysDir = path.join(__dirname, '..', 'keys');
  fs.mkdirSync(keysDir, { recursive: true });
  const keyPath = path.join(keysDir, 'master.json');

  let keyPair;
  if (fs.existsSync(keyPath)) {
    const saved = JSON.parse(fs.readFileSync(keyPath, 'utf8'));
    if (saved.account_id === accountId) {
      console.log(`Reusing existing key for ${accountId}`);
      keyPair = KeyPair.fromString(saved.secret_key);
    }
  }
  if (!keyPair) {
    keyPair = KeyPair.fromRandom('ed25519');
    fs.writeFileSync(keyPath, JSON.stringify({
      account_id: accountId,
      public_key: keyPair.getPublicKey().toString(),
      secret_key: keyPair.toString(),
    }, null, 2), { mode: 0o600 });
    console.log(`Generated new keypair for ${accountId}`);
  }
  const publicKey = keyPair.getPublicKey().toString();
  console.log(`Public key: ${publicKey}`);

  console.log(`POST ${HELPER_URL} ...`);
  const res = await fetch(HELPER_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ newAccountId: accountId, newAccountPublicKey: publicKey }),
  });
  const body = await res.text();
  console.log(`Helper status: ${res.status}`);
  console.log(`Helper body: ${body.slice(0, 500)}`);
  if (!res.ok && !body.includes('already exists') && res.status !== 400) {
    throw new Error(`Account creation failed (HTTP ${res.status})`);
  }

  // Verify over RPC: query the account.
  const keyStore = new keyStores.InMemoryKeyStore();
  await keyStore.setKey('testnet', accountId, keyPair);
  const near = await connect({ networkId: 'testnet', keyStore, nodeUrl: RPC_URL });
  const account = await near.account(accountId);
  const state = await account.state();
  const balanceNear = Number(state.amount) / 1e24;
  console.log(`VERIFIED: ${accountId} exists on testnet`);
  console.log(`  balance: ${balanceNear} NEAR (${state.amount} yocto)`);
  console.log(`  storage used: ${state.storage_usage} bytes, block height ${state.block_height}`);
  console.log(`  code hash: ${state.code_hash}`);
  return { accountId, balanceNear };
}

main().catch((e) => { console.error('FAILED:', e.message); process.exit(1); });
