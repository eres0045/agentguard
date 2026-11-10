// Day-1 spike, steps 3-6: deploy the vault contract to the master account,
// initialise policy (per-tx cap 1 NEAR, daily cap 5 NEAR), create the vendor
// sub-account, allowlist it, add the agent's function-call key (pay only,
// 0.25 NEAR allowance), then run the agent's first LEGIT payment through
// the scoped key and print the real tx hash.
// Usage: node scripts/deploy-vault.js
// Writes real hashes to spike-results.json.
const fs = require('fs');
const path = require('path');
const { KeyPair, keyStores, connect, utils } = require('near-api-js');

const RPC_URL = 'https://rpc.testnet.near.org';
const EXPLORER = 'https://explorer.testnet.near.org/transactions/';
const GAS = BigInt('100000000000000'); // 100 TGas
const NEAR = (n) => utils.format.parseNearAmount(String(n));

async function main() {
  const root = path.join(__dirname, '..');
  const keysDir = path.join(root, 'keys');
  const master = JSON.parse(fs.readFileSync(path.join(keysDir, 'master.json'), 'utf8'));
  const fnKeySaved = JSON.parse(fs.readFileSync(path.join(keysDir, 'agent-function-call.json'), 'utf8'));
  const masterId = master.account_id;
  const vendorId = `vendor.${masterId}`;
  const results = { master: masterId, vendor: vendorId, steps: [] };
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

  // 1. Deploy contract code to the master account (the vault IS the master).
  const wasm = fs.readFileSync(path.join(root, 'contract', 'target', 'wasm32-unknown-unknown', 'release', 'agentguard_vault.wasm'));
  const deployTx = await masterAccount.deployContract(wasm);
  log('deploy_contract', { tx_hash: deployTx.transaction.hash, explorer: EXPLORER + deployTx.transaction.hash, wasm_bytes: wasm.length });

  // 2. Initialise: owner=master, per-tx cap 1 NEAR, daily cap 5 NEAR.
  const initTx = await masterAccount.functionCall({
    contractId: masterId, methodName: 'new',
    args: { owner: masterId, per_tx_cap: NEAR('1'), daily_cap: NEAR('5') },
    gas: GAS, attachedDeposit: BigInt(0),
  });
  log('init_policy', { tx_hash: initTx.transaction.hash, explorer: EXPLORER + initTx.transaction.hash, per_tx_cap: '1 NEAR', daily_cap: '5 NEAR' });

  // 3. Create vendor sub-account (the allowlisted payee) if needed.
  const vendorKey = KeyPair.fromRandom('ed25519');
  try {
    await masterAccount.createAccount(vendorId, vendorKey.getPublicKey(), NEAR('0.1'));
    log('create_vendor', { vendor: vendorId, funded: '0.1 NEAR' });
  } catch (e) {
    log('create_vendor', { vendor: vendorId, note: 'already exists (skipped)', error: String(e.message).slice(0, 120) });
  }

  // 4. Allowlist the vendor (owner-only contract call).
  const allowTx = await masterAccount.functionCall({
    contractId: masterId, methodName: 'add_recipient',
    args: { account: vendorId }, gas: GAS, attachedDeposit: BigInt(0),
  });
  log('allowlist_vendor', { tx_hash: allowTx.transaction.hash, explorer: EXPLORER + allowTx.transaction.hash });

  // 5. Add the agent's function-call key: ONLY method `pay` on this contract,
  //    allowance 0.25 NEAR (gas budget only — it cannot move funds by itself).
  const addKeyTx = await masterAccount.addKey(
    fnKey.getPublicKey(), masterId, ['pay'], NEAR('0.25'),
  );
  log('add_agent_function_call_key', {
    tx_hash: addKeyTx.transaction.hash,
    explorer: EXPLORER + addKeyTx.transaction.hash,
    public_key: fnKey.getPublicKey().toString(),
    receiver: masterId, methods: ['pay'], allowance: '0.25 NEAR',
  });

  // 6. THE SPIKE: the agent (function-call key only, never the master key)
  //    pays 0.5 NEAR to the allowlisted vendor through the vault contract.
  const agentKeyStore = new keyStores.InMemoryKeyStore();
  await agentKeyStore.setKey('testnet', masterId, fnKey);
  const agentNear = await connect({ networkId: 'testnet', keyStore: agentKeyStore, nodeUrl: RPC_URL });
  const agentAsVaultCaller = await agentNear.account(masterId);
  const payTx = await agentAsVaultCaller.functionCall({
    contractId: masterId, methodName: 'pay',
    args: { recipient: vendorId, amount: NEAR('0.5') },
    gas: GAS, attachedDeposit: BigInt(0),
  });
  const payHash = payTx.transaction.hash;
  log('agent_legit_pay', {
    tx_hash: payHash, explorer: EXPLORER + payHash,
    from: 'agent function-call key', to: vendorId, amount: '0.5 NEAR',
    status: JSON.stringify(payTx.status),
  });

  // 7. Verify on-chain: vault policy + vendor balance.
  const policy = await masterAccount.viewFunction({ contractId: masterId, methodName: 'get_policy', args: {} });
  const vendorAccount = await near.account(vendorId);
  const vendorState = await vendorAccount.state();
  log('verify', {
    daily_spent_yocto: policy.daily_spent,
    daily_spent_near: Number(policy.daily_spent) / 1e24,
    killed: policy.killed,
    allowlist: policy.allowlist,
    vendor_balance_near: Number(vendorState.amount) / 1e24,
  });

  fs.writeFileSync(path.join(root, 'spike-results.json'), JSON.stringify(results, null, 2));
  console.log('\nSPIKE COMPLETE — results in spike-results.json');
}

main().catch((e) => { console.error('FAILED:', e); process.exit(1); });
