"""AgentGuard policy engine — pure Python, no chain access, fully unit-testable.

Decision order for a payment request (recipient, amount_near):
  1. KILLED?            -> BLOCKED (vault killed / key revoked)
  2. RULES (hard):      allowlist, per-tx cap, daily cap, velocity
                        -> any violation = BLOCKED, never reaches the chain
  3. CLASSIFIER:        TF score P(attack); score >= 0.5 = suspicious
  4. APPROVAL THRESHOLD: amount > approval_threshold_near, or suspicious
                        -> QUEUED for one-click human approve/reject
  5. otherwise          -> EXECUTE via the agent's scoped function-call key

The on-chain contract re-enforces (1)-(2) independently: even if this
engine is bypassed, the vault contract blocks the same violations.
"""
from dataclasses import dataclass, field

APPROVAL_THRESHOLD_NEAR = 1.0   # >1 NEAR always needs a human, even under the cap
VELOCITY_MAX_PER_MIN = 3        # >3 payments in a rolling 60s window = burst
CLASSIFIER_FLAG_THRESHOLD = 0.5


@dataclass
class PolicyConfig:
    per_tx_cap_near: float = 2.0
    daily_cap_near: float = 10.0
    daily_spent_near: float = 0.0
    allowlist: set = field(default_factory=set)
    killed: bool = False
    approval_threshold_near: float = APPROVAL_THRESHOLD_NEAR


@dataclass
class Decision:
    verdict: str  # EXECUTE | QUEUE | BLOCK
    reasons: list
    classifier_score: float = 0.0

    def to_dict(self):
        return {"verdict": self.verdict, "reasons": self.reasons,
                "classifier_score": round(self.classifier_score, 4)}


def decide(cfg: PolicyConfig, recipient: str, amount_near: float,
           recent_tx_count_60s: int, classifier_score: float) -> Decision:
    """Pure rule evaluation. `classifier_score` is P(attack) in [0, 1]."""
    reasons = []
    if cfg.killed:
        return Decision("BLOCK", ["vault is killed"], classifier_score)
    if amount_near <= 0:
        return Decision("BLOCK", ["amount must be positive"], classifier_score)
    if recipient not in cfg.allowlist:
        reasons.append(f"recipient {recipient} is not on the allowlist")
    if amount_near > cfg.per_tx_cap_near:
        reasons.append(f"amount {amount_near} exceeds per-tx cap {cfg.per_tx_cap_near} NEAR")
    if cfg.daily_spent_near + amount_near > cfg.daily_cap_near:
        reasons.append(
            f"amount exceeds remaining daily cap "
            f"({cfg.daily_cap_near - cfg.daily_spent_near:.4f} NEAR left)")
    if recent_tx_count_60s >= VELOCITY_MAX_PER_MIN:
        reasons.append(
            f"velocity: {recent_tx_count_60s} payments in the last 60s "
            f"(max {VELOCITY_MAX_PER_MIN}) — possible burst")
    if reasons:
        return Decision("BLOCK", reasons, classifier_score)

    if classifier_score >= CLASSIFIER_FLAG_THRESHOLD:
        reasons.append(f"classifier flagged this payment (attack score {classifier_score:.2f})")
        return Decision("QUEUE", reasons, classifier_score)
    if amount_near > cfg.approval_threshold_near:
        reasons.append(
            f"amount {amount_near} NEAR exceeds auto-approve threshold "
            f"{cfg.approval_threshold_near} NEAR — human approval required")
        return Decision("QUEUE", reasons, classifier_score)
    return Decision("EXECUTE", ["within caps, allowlisted, classifier clean"], classifier_score)


def features(amount_near: float, allowlisted: bool, per_tx_cap_near: float,
             daily_remaining_near: float, recent_tx_count_60s: int) -> list:
    """Feature vector for the classifier — same order as training."""
    import math
    return [
        math.log1p(amount_near),
        1.0 if allowlisted else 0.0,
        min(amount_near / per_tx_cap_near, 5.0) if per_tx_cap_near > 0 else 5.0,
        min(amount_near / daily_remaining_near, 5.0) if daily_remaining_near > 0 else 5.0,
        min(recent_tx_count_60s / 3.0, 3.0),
    ]
