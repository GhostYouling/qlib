from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign100_features as c100
from scripts import a_share_three_day_walkforward_campaign101_features as c101

ROOT = Path(__file__).resolve().parents[2]
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_101_terminal_result_binding_v2_20260807.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_101/research_attempt_ledger_v14.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v56_20260807.json"
)
SURVIVORS = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_101/walkforward/development_survivors.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_corrected_terminal_bindings_and_reports_have_exact_hashes() -> None:
    assert _sha256(RESULT) == (
        "749a6a4e8393e2c44aab9c956563dc6d3dfd06749051bea7bf51a27df7d0b18d"
    )
    assert _sha256(LEDGER) == (
        "21c341d2caf61f40374bb5fbaae8a239ec01f71dfbd107ffc36a615f3f7e0929"
    )
    assert _sha256(POLICY) == (
        "25025b07a3e9690c43486b64f14a76530600819fc90b1ed8d4551bc15003fa0e"
    )
    assert _sha256(SURVIVORS) == (
        "a9a704c37e6975f4cf54f7e245d0d7ad689fda3f224539b81979c1cf56303e1c"
    )
    assert _sha256(
        ROOT / "docs/a_share_three_day_walkforward_campaign_101_report.md"
    ) == ("afeaecde1da09091e5e72b4f8b4c7c95760af153ad65aa64e6b6a60166916bca")
    assert (
        _sha256(ROOT / "data/experiments/short_horizon/three_day_research_report.md")
        == "2d37b05e4ceb26866decdd3d4936df49951970c9ed47ad71210df2b89605a011"
    )
    assert (
        _sha256(ROOT / "data/experiments/short_horizon/current_research_report.md")
        == "61117fcb2788f8e24c37a95423bf0602896c6418cc0e40b23f8920f3561cb6ac"
    )


def test_v2_changes_only_binding_and_additive_accounting() -> None:
    result = _load(RESULT)
    terminal = result["terminal_result"]
    assert result["supersedes_without_rewriting"]["scientific_result_changed"] is False
    assert terminal["development_survivor_count"] == 0
    assert terminal["development_aggregate_20bp_return"] == -0.21717077405952845
    assert terminal["stress_2024_2025_opened"] is False
    assert (
        result["research_boundary"][
            "formula_factor_values_folds_cost_gates_metrics_or_survivors_changed_by_v2"
        ]
        is False
    )
    assert result["research_boundary"]["additional_research_values_read_by_v2"] is False


def test_v56_preserves_exact_v55_orders() -> None:
    policy = _load(POLICY)
    c100_item = {"name": c100.FACTOR_NAME, "score_direction": "higher"}
    c101_item = {"name": c101.FACTOR_NAME, "score_direction": "higher"}
    complete = c100.reconstruct_complete_definitions() + [c100_item, c101_item]
    numeric = c100.reconstruct_comparisons() + [c100_item, c101_item]
    assert (
        len(complete)
        == policy["complete_historical_feature_library"]["factor_definition_count"]
        == 133
    )
    assert (
        c100._order_digest(complete)
        == policy["complete_historical_feature_library"]["order_sha256"]
    )
    assert (
        len(numeric)
        == policy["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_count"
        ]
        == 130
    )
    assert (
        c100._order_digest(numeric)
        == policy["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_order_sha256"
        ]
    )


def test_final_accounting_includes_binding_failure_only_once() -> None:
    ledger = _load(LEDGER)
    assert ledger["campaign101_attempt_count"] == 20
    assert ledger["campaign101_ledger_entry_count"] == 20
    assert (
        ledger["campaign101_infrastructure_implementation_or_recording_failure_count"]
        == 13
    )
    assert ledger["campaign101_return_reading_development_trial_count"] == 1
    assert ledger["campaign101_development_survivor_count"] == 0
    assert ledger["campaign101_stress_trial_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 744
    assert ledger["cumulative_return_reading_development_trial_count"] == 295


def test_candidate49_remains_empty_and_unchanged() -> None:
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
