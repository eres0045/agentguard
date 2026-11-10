//! AgentGuard vault contract (NEAR testnet).
//!
//! The AI agent NEVER holds the master key. It holds only a NEAR
//! function-call access key restricted to this contract's `pay` method.
//! This contract is the second, on-chain line of defence: even if the
//! off-chain policy engine is bypassed, a payment can only move if
//!   1. the contract is not killed,
//!   2. the recipient is on the allowlist,
//!   3. the amount is within the per-transaction cap, and
//!   4. the amount fits inside the remaining daily cap.
//!
//! The owner (master account, full-access key) manages the allowlist and
//! caps, and can `kill` the vault permanently. Revocation of the agent
//! itself is a `DeleteKey` action on the vault account, done by the
//! backend kill switch — after that the agent cannot even call `pay`.

use near_sdk::json_types::U128;
use near_sdk::serde::Serialize;
use near_sdk::store::UnorderedSet;
use near_sdk::{env, near, AccountId, NearToken, PanicOnDefault, Promise};

const NS_PER_DAY: u64 = 86_400_000_000_000;

#[near(contract_state)]
#[derive(PanicOnDefault)]
pub struct Vault {
    owner: AccountId,
    per_tx_cap: u128, // yoctoNEAR
    daily_cap: u128,  // yoctoNEAR
    daily_spent: u128,
    day: u64, // epoch day number (block_timestamp / NS_PER_DAY)
    allowlist: UnorderedSet<AccountId>,
    killed: bool,
}

#[derive(Serialize)]
#[serde(crate = "near_sdk::serde")]
pub struct Policy {
    owner: AccountId,
    per_tx_cap: U128,
    daily_cap: U128,
    daily_spent: U128,
    day: u64,
    killed: bool,
    allowlist: Vec<AccountId>,
}

#[near]
impl Vault {
    #[init]
    pub fn new(owner: AccountId, per_tx_cap: U128, daily_cap: U128) -> Self {
        Self {
            owner,
            per_tx_cap: per_tx_cap.0,
            daily_cap: daily_cap.0,
            daily_spent: 0,
            day: env::block_timestamp() / NS_PER_DAY,
            allowlist: UnorderedSet::new(b"a"),
            killed: false,
        }
    }

    fn assert_owner(&self) {
        assert_eq!(
            env::predecessor_account_id(),
            self.owner,
            "only the vault owner (master) can call this"
        );
    }

    fn assert_alive(&self) {
        assert!(!self.killed, "vault is killed: no payments possible");
    }

    fn rollover_day(&mut self) {
        let today = env::block_timestamp() / NS_PER_DAY;
        if today != self.day {
            self.day = today;
            self.daily_spent = 0;
        }
    }

    /// The ONLY method the agent's function-call key may call.
    /// Enforces allowlist + per-tx cap + daily cap on-chain, then transfers
    /// from the vault's own balance.
    pub fn pay(&mut self, recipient: AccountId, amount: U128) -> U128 {
        self.assert_alive();
        let amount = amount.0;
        assert!(amount > 0, "amount must be positive");
        assert!(
            self.allowlist.contains(&recipient),
            "recipient is not on the allowlist"
        );
        assert!(
            amount <= self.per_tx_cap,
            "amount exceeds per-transaction cap"
        );
        self.rollover_day();
        assert!(
            self.daily_spent + amount <= self.daily_cap,
            "amount exceeds remaining daily cap"
        );
        self.daily_spent += amount;
        Promise::new(recipient).transfer(NearToken::from_yoctonear(amount));
        U128(self.daily_spent)
    }

    // ---- owner-only management ----

    pub fn add_recipient(&mut self, account: AccountId) {
        self.assert_owner();
        self.allowlist.insert(account);
    }

    pub fn remove_recipient(&mut self, account: AccountId) {
        self.assert_owner();
        self.allowlist.remove(&account);
    }

    pub fn set_caps(&mut self, per_tx_cap: U128, daily_cap: U128) {
        self.assert_owner();
        self.per_tx_cap = per_tx_cap.0;
        self.daily_cap = daily_cap.0;
    }

    /// One-way kill switch at the contract level. After this, `pay` always
    /// fails. (The backend kill switch additionally deletes the agent's
    /// function-call key, so the agent cannot even reach this contract.)
    pub fn kill(&mut self) {
        self.assert_owner();
        self.killed = true;
    }

    // ---- views ----

    pub fn get_policy(&self) -> Policy {
        Policy {
            owner: self.owner.clone(),
            per_tx_cap: U128(self.per_tx_cap),
            daily_cap: U128(self.daily_cap),
            daily_spent: U128(self.daily_spent),
            day: self.day,
            killed: self.killed,
            allowlist: self.allowlist.iter().cloned().collect(),
        }
    }

    pub fn is_allowed(&self, account: AccountId) -> bool {
        self.allowlist.contains(&account)
    }

    pub fn get_daily_spent(&self) -> U128 {
        U128(self.daily_spent)
    }

    pub fn is_killed(&self) -> bool {
        self.killed
    }
}
