"""Policy engine unit tests — pure Python, no chain, no network."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from policy import (APPROVAL_THRESHOLD_NEAR, CLASSIFIER_FLAG_THRESHOLD,
                    PolicyConfig, decide)


def cfg(**over):
    base = dict(per_tx_cap_near=2.0, daily_cap_near=10.0, daily_spent_near=0.6,
                allowlist={"vendor.fortec-agentguard.testnet"}, killed=False)
    base.update(over)
    return PolicyConfig(**base)


def test_legit_small_payment_executes():
    d = decide(cfg(), "vendor.fortec-agentguard.testnet", 0.5, 0, 0.05)
    assert d.verdict == "EXECUTE"


def test_non_allowlisted_recipient_blocked():
    d = decide(cfg(), "attacker.evil.testnet", 0.5, 0, 0.05)
    assert d.verdict == "BLOCK"
    assert "allowlist" in d.reasons[0]


def test_over_cap_blocked():
    d = decide(cfg(), "vendor.fortec-agentguard.testnet", 3.0, 0, 0.05)
    assert d.verdict == "BLOCK"
    assert any("per-tx cap" in r for r in d.reasons)


def test_exactly_at_cap_executes():
    d = decide(cfg(), "vendor.fortec-agentguard.testnet", 2.0, 0, 0.05)
    assert d.verdict == "QUEUE"  # at cap but over the 1 NEAR approval threshold


def test_daily_cap_blocked():
    d = decide(cfg(daily_spent_near=9.5), "vendor.fortec-agentguard.testnet", 1.0, 0, 0.05)
    assert d.verdict == "BLOCK"
    assert any("daily cap" in r for r in d.reasons)


def test_over_approval_threshold_queued():
    d = decide(cfg(), "vendor.fortec-agentguard.testnet", 1.5, 0, 0.05)
    assert d.verdict == "QUEUE"
    assert any("approval" in r for r in d.reasons)


def test_classifier_flag_queued_even_when_small():
    d = decide(cfg(), "vendor.fortec-agentguard.testnet", 0.5, 0, 0.87)
    assert d.verdict == "QUEUE"
    assert any("classifier" in r for r in d.reasons)


def test_classifier_threshold_boundary():
    d = decide(cfg(), "vendor.fortec-agentguard.testnet", 0.5, 0, CLASSIFIER_FLAG_THRESHOLD)
    assert d.verdict == "QUEUE"
    d2 = decide(cfg(), "vendor.fortec-agentguard.testnet", 0.5, 0, CLASSIFIER_FLAG_THRESHOLD - 0.01)
    assert d2.verdict == "EXECUTE"


def test_burst_velocity_blocked():
    d = decide(cfg(), "vendor.fortec-agentguard.testnet", 0.2, 3, 0.05)
    assert d.verdict == "BLOCK"
    assert any("velocity" in r for r in d.reasons)


def test_two_recent_payments_still_execute():
    d = decide(cfg(), "vendor.fortec-agentguard.testnet", 0.2, 2, 0.05)
    assert d.verdict == "EXECUTE"


def test_killed_vault_blocks_everything():
    d = decide(cfg(killed=True), "vendor.fortec-agentguard.testnet", 0.1, 0, 0.0)
    assert d.verdict == "BLOCK"


def test_zero_and_negative_amounts_blocked():
    assert decide(cfg(), "vendor.fortec-agentguard.testnet", 0, 0, 0.0).verdict == "BLOCK"
    assert decide(cfg(), "vendor.fortec-agentguard.testnet", -1, 0, 0.0).verdict == "BLOCK"


def test_multiple_violations_all_reported():
    d = decide(cfg(), "attacker.evil.testnet", 50.0, 0, 0.99)
    assert d.verdict == "BLOCK"
    assert len(d.reasons) >= 3  # allowlist + per-tx cap + daily cap


def test_approval_threshold_constant():
    assert APPROVAL_THRESHOLD_NEAR == 1.0
