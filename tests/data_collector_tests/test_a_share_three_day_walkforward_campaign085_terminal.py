from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign085_features as features

ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "docs/a_share_three_day_walkforward_campaign_085_research_record.json"
CURRENT_RECORD = (
    ROOT / "docs/a_share_three_day_walkforward_campaign_085_research_record_v4.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v24_20260807.json"
)
WALKFORWARD = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_085/walkforward"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_terminal_record_binds_completed_zero_survivor_lifecycle() -> None:
    record = _load(RECORD)
    assert _sha256(RECORD) == (
        "31c42ec3e59616c94bb81df78476e5652f6528a666fc54b092f2bc3035d74c6f"
    )
    assert record["status"] == "terminal_zero_development_survivors_stress_closed"
    assert record["development_trial"]["trial_count"] == 1
    decision = record["development_trial"]["survivor_decision"]
    assert decision["development_survivor_count"] == 0
    assert decision["operationally_admissible"] is True
    assert decision["validation_quality_gate_passed"] is False
    assert record["stress_2024_2025"] == {
        "opened": False,
        "reason": "zero development survivors",
        "return_fields_read": False,
    }
    current = _load(CURRENT_RECORD)
    assert current["status"] == (
        "terminal_zero_development_survivors_stress_closed_current_suite_verified"
    )
    assert current["scientific_record"]["sha256"] == _sha256(RECORD)


def test_terminal_walkforward_artifacts_and_rejection_metrics_are_frozen() -> None:
    record = _load(RECORD)
    bindings = record["walkforward_bindings"]
    for key in ("trial_ledger", "survivor_record", "stress_record", "campaign_report"):
        binding = bindings[key]
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    ledger = _load(WALKFORWARD / "trial_ledger.json")
    assert [entry["phase"] for entry in ledger["entries"]] == [
        "infrastructure_failure",
        "development_walkforward_2019_2023",
    ]
    assert ledger["chain_tip_sha256"] == (
        "0040c3b08da365ae9e543d9d579910a7b1a92d2f1ac792ab9cd73f58bb76cddd"
    )
    decision = _load(WALKFORWARD / "development_survivors.json")["trial_decisions"][0]
    assert decision["development_aggregate_20bp_return"] == -0.26190957429226913
    assert decision["positive_pilot_return_fold_count"] == 0
    assert decision["worst_validation_normalized_drawdown"] == -0.5019995808847861


def test_stress_closed_record_and_attempt_accounting_are_exact() -> None:
    stress = _load(WALKFORWARD / "exposed_stress_consumption_record.json")
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    ledger_path = (
        ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_085/research_attempt_ledger_v28.json"
    )
    ledger = _load(ledger_path)
    assert _sha256(ledger_path) == (
        "291f87fb39b51132cb4ab2de66e833fe721ca7341652195ef6399e0a7ccc7ca3"
    )
    assert ledger["campaign085_attempt_count"] == 27
    assert ledger["campaign085_infrastructure_failure_count"] == 26
    assert ledger["campaign085_return_reading_development_trial_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 572
    assert ledger["cumulative_return_reading_development_trial_count"] == 285


def test_current_future_library_appends_terminal_campaign085_once() -> None:
    policy = _load(POLICY)
    assert _sha256(POLICY) == (
        "47d582150f3cca9c00f919e397600b388d65505e1f97d62017a693520d2828e1"
    )
    candidate = {"name": features.FACTOR_NAME, "score_direction": "higher"}
    complete = features.reconstruct_complete_definitions() + [candidate]
    numeric = features.reconstruct_comparisons() + [candidate]
    assert len(complete) == 117
    assert len(numeric) == 115
    assert features._comparison_order_digest(complete) == (
        "462cd7b3aa1d7cd909e35b050025cf21094954b1f76925833f46f65c4d1317f8"
    )
    assert features._comparison_order_digest(numeric) == (
        "f22759b26333f8e1fdb5a8ca942afa96aca88b544311e608fd9ffbd5105c80ab"
    )
    assert policy["numerical_comparator_eligibility"][
        "eligible_numeric_comparator_count"
    ] == len(numeric)
    assert (
        policy["research_boundary"][
            "campaign086_candidate_or_comparison_values_read_before_v24_freeze"
        ]
        is False
    )
