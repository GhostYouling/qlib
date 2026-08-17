from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign100_features as c100
from scripts import a_share_three_day_walkforward_campaign101_features as c101

ROOT = Path(__file__).resolve().parents[2]
WALKFORWARD = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_101/walkforward"
)
TRIAL_LEDGER = WALKFORWARD / "trial_ledger.json"
SURVIVORS = WALKFORWARD / "development_survivors.json"
STRESS = WALKFORWARD / "exposed_stress_consumption_record.json"
GENERATED_REPORT = WALKFORWARD / "campaign_report.json"
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_101_terminal_result_binding_20260807.json"
)
ATTEMPT_LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_101/research_attempt_ledger_v13.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v55_20260807.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_terminal_artifact_hashes_are_exact() -> None:
    assert _sha256(TRIAL_LEDGER) == (
        "c72a835598e85b7829a019ed03911ca67606528da6fcf3378ae2fc7933cc61bd"
    )
    assert _sha256(SURVIVORS) == (
        "a9a704c37e6975f4cf54f7e245d0d7ad689fda3f224539b81979c1cf56303e1c"
    )
    assert _sha256(STRESS) == (
        "d4bec7ae46b64d65840953feb77686ad680df2a3b660481a1d9f012ec78637d0"
    )
    assert _sha256(GENERATED_REPORT) == (
        "7416eb1a02049b10c3a3fa781af0ac66988e44bee0c35b02fb67178fd98b9867"
    )
    assert _sha256(RESULT) == (
        "0ff78e9319d04fb687a92dbe5b1ee43ff8bf707609f8fceca603d7c40aef6862"
    )
    assert _sha256(ATTEMPT_LEDGER) == (
        "d86b6f57218abc9909d32f67abf009ad0408070772be9ae18f2fedc4f4816f87"
    )
    assert _sha256(POLICY) == (
        "5bf1898a106589ae127656405e0083dbcf36864249a6500d95be1a06281e299d"
    )


def test_single_development_trial_is_complete_and_has_zero_survivors() -> None:
    ledger = _load(TRIAL_LEDGER)
    infrastructure = [
        item for item in ledger["entries"] if item["phase"] == "infrastructure_failure"
    ]
    development = [
        item
        for item in ledger["entries"]
        if item["phase"] == "development_walkforward_2019_2023"
    ]
    assert len(infrastructure) == 2
    assert len(development) == 1
    assert development[0]["trial_id"] == (
        "wf101_full_numeric_library_directional_lower_quartile_consensus_129f_single_higher"
    )
    assert development[0]["status_and_rejection_reason"]["status"] == (
        "development_walkforward_completed"
    )
    survivor = _load(SURVIVORS)
    assert survivor["selected_survivor_count"] == 0
    assert survivor["trial_decisions"][0]["development_survivor_gate_passed"] is False


def test_fold_metrics_and_frozen_rejection_reasons_are_exact() -> None:
    result = _load(RESULT)
    folds = result["development"]["fold_metrics"]
    assert [item["validation_year"] for item in folds] == [2021, 2022, 2023]
    assert [item["mean_rank_ic"] for item in folds] == [
        -0.024094659583741525,
        -0.010091585425579487,
        -0.03791009349317091,
    ]
    assert [item["normalized_return"] for item in folds] == [
        -0.22509634735460682,
        -0.17176791661162094,
        -0.06828092859635215,
    ]
    decision = result["development"]["survivor_decision"]
    assert decision["positive_mean_rank_ic_fold_count"] == 0
    assert decision["positive_normalized_return_fold_count"] == 0
    assert decision["positive_pilot_return_fold_count"] == 0
    assert decision["development_aggregate_20bp_return"] == -0.21717077405952845
    assert decision["worst_validation_normalized_drawdown"] == (-0.35020163110644087)
    assert len(decision["rejection_reasons"]) == 7


def test_stress_2024_2025_is_closed_and_unread() -> None:
    stress = _load(STRESS)
    result = _load(RESULT)
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    assert result["exposed_stress"]["interval_2024_2025_opened"] is False
    assert result["exposed_stress"]["return_fields_read"] is False
    assert result["exposed_stress"]["stress_trial_count"] == 0


def test_v55_orders_append_campaign101_exactly_once() -> None:
    policy = _load(POLICY)
    c100_item = {"name": c100.FACTOR_NAME, "score_direction": "higher"}
    c101_item = {"name": c101.FACTOR_NAME, "score_direction": "higher"}
    complete = c100.reconstruct_complete_definitions() + [c100_item, c101_item]
    numeric = c100.reconstruct_comparisons() + [c100_item, c101_item]
    complete_policy = policy["complete_historical_feature_library"]
    numeric_policy = policy["numerical_comparator_eligibility"]
    assert len(complete) == complete_policy["factor_definition_count"] == 133
    assert c100._order_digest(complete) == complete_policy["order_sha256"]
    assert len(numeric) == numeric_policy["eligible_numeric_comparator_count"] == 130
    assert (
        c100._order_digest(numeric)
        == numeric_policy["eligible_numeric_comparator_order_sha256"]
    )
    assert numeric_policy["last_comparator"][
        "numeric_comparator_eligible_for_campaign102"
    ]


def test_effective_attempt_accounting_is_append_only() -> None:
    ledger = _load(ATTEMPT_LEDGER)
    assert ledger["campaign101_attempt_count"] == 19
    assert ledger["campaign101_ledger_entry_count"] == 19
    assert (
        ledger["campaign101_infrastructure_implementation_or_recording_failure_count"]
        == 12
    )
    assert ledger["campaign101_return_reading_development_trial_count"] == 1
    assert ledger["campaign101_development_survivor_count"] == 0
    assert ledger["campaign101_stress_trial_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 743
    assert ledger["cumulative_return_reading_development_trial_count"] == 295


def test_generated_report_count_scope_is_explicitly_corrected() -> None:
    generated = _load(GENERATED_REPORT)
    result = _load(RESULT)
    assert generated["infrastructure_failure_count"] == 0
    reporting = result["reporting_semantics"]
    assert (
        reporting[
            "authoritative_infrastructure_failure_count_uses_trial_ledger_phase_entries"
        ]
        == 2
    )
    assert (
        reporting[
            "generated_campaign_report_infrastructure_failure_count_field_is_authoritative"
        ]
        is False
    )


def test_reports_expose_campaign101_terminal_result() -> None:
    paths = [
        ROOT / "docs/a_share_three_day_walkforward_campaign_101_report.md",
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "Campaign101" in text
        assert "0.557897" in text
        assert "-21.717077%" in text
        assert "2024–2025" in text


def test_candidate49_ledgers_are_empty_and_unchanged() -> None:
    signal = (
        ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    )
    execution = (
        ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    )
    assert _sha256(signal) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha256(execution) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert _load(signal)["entries"] == []
    assert _load(execution)["entries"] == []
