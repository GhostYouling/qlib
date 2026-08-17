from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign100_features as inventory
from scripts import a_share_three_day_walkforward_campaign101_features as c101
from scripts import a_share_three_day_walkforward_campaign103 as c103

ROOT = Path(__file__).resolve().parents[2]
CORRECTION = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_103_postterminal_logical_timestamp_failure_20260808.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_103/research_attempt_ledger_v2.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_103_terminal_result_binding_v2_20260808.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v61_20260808.json"
)
STATE = ROOT / "docs/a_share_three_day_iteration_status_20260808_campaign103_terminal_v2.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_effective_timestamp_correction_artifact_hashes_are_exact() -> None:
    assert _sha256(CORRECTION) == (
        "cb9ad7fe1d477ee93ca7a6d02c84a1333d5679cefb86744baab7bdb00a1bbd47"
    )
    assert _sha256(LEDGER) == (
        "03a6b9789421d6503f63d917b033d046613a0a34d3609376d248391674157174"
    )
    assert _sha256(RESULT) == (
        "f533467879a962068e24d1c1b07d814f3458f6e20c83221a240ba2dfbd55ab38"
    )
    assert _sha256(POLICY) == (
        "bfced9733feba5975bc46b96f2596a9227a160849dbf50b41c958053edcc59a0"
    )
    assert _sha256(STATE) == (
        "7d1aa661066c7445bb9e2e2b984e8b2b9042f1b044f3b9defc30d69e7e52a4e2"
    )


def test_correction_counts_common_root_once_without_changing_science() -> None:
    correction = _load(CORRECTION)
    assert len(correction["affected_artifacts"]) == 11
    assert all(item["declared_time_was_after_write"] for item in correction["affected_artifacts"])
    assert correction["research_values_or_returns_recomputed"] is False
    assert correction["scientific_result_changed"] is False
    result = _load(RESULT)
    assert result["supersedes_without_rewriting"]["scientific_result_changed"] is False
    assert result["scientific_result"]["development_survivor_count"] == 0
    assert result["scientific_result"]["stress_2024_2025_opened"] is False


def test_effective_attempt_accounting_is_15_attempts_and_14_failures() -> None:
    ledger = _load(LEDGER)
    assert ledger["attempt_count"] == len(ledger["entries"]) == 15
    assert ledger["infrastructure_failure_count"] == 14
    assert ledger["complete_factor_attempt_count"] == 1
    assert ledger["return_reading_complete_development_trial_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 768
    assert ledger["cumulative_return_reading_development_trial_count"] == 299
    assert ledger["entries"][-1]["attempt_id"] == "campaign103_infrastructure_015"


def test_v61_preserves_v60_exact_134_and_131_orders() -> None:
    policy = _load(POLICY)
    c100_item = {"name": inventory.FACTOR_NAME, "score_direction": "higher"}
    c101_item = {"name": c101.FACTOR_NAME, "score_direction": "higher"}
    c103_item = {"name": c103.ADMITTED_FACTOR, "score_direction": "higher"}
    complete = inventory.reconstruct_complete_definitions() + [c100_item, c101_item, c103_item]
    numeric = inventory.reconstruct_comparisons() + [c100_item, c101_item, c103_item]
    assert len(complete) == policy["complete_historical_feature_library"]["factor_definition_count"] == 134
    assert inventory._order_digest(complete) == policy["complete_historical_feature_library"]["order_sha256"]
    assert len(numeric) == policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"] == 131
    assert inventory._order_digest(numeric) == policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_order_sha256"]


def test_effective_state_and_reports_use_corrected_accounting() -> None:
    state = _load(STATE)
    assert state["accounting"]["campaign103_attempt_count"] == 15
    assert state["accounting"]["campaign103_infrastructure_failure_count"] == 14
    assert state["accounting"]["cumulative_historical_research_attempt_count"] == 768
    assert state["campaign103_terminal"]["development_survivor_count"] == 0
    assert state["candidate49"]["signal_entry_count"] == 0
    assert state["candidate49"]["execution_entry_count"] == 0
    for path in (
        ROOT / "docs/a_share_three_day_walkforward_campaign_103_report.md",
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "15 次" in text
        assert "768" in text
        assert "v61" in text
