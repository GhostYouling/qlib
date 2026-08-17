from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign100_features as c100
from scripts import a_share_three_day_walkforward_campaign101_features as c101

ROOT = Path(__file__).resolve().parents[2]
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_101_terminal_result_binding_v3_20260807.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_101/research_attempt_ledger_v15.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v57_20260807.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_effective_v3_artifact_hashes_are_exact() -> None:
    assert _sha256(RESULT) == (
        "c21e6c64dfd285de3c9f890ca15c5a4bd3a84d2324a44b0ce6c4025cf846af49"
    )
    assert _sha256(LEDGER) == (
        "7342cdf880fed5b1ae80ad4989678d4da73a28a7dc57a287ce9dca3846731ff7"
    )
    assert _sha256(POLICY) == (
        "1071ea3246a889054ffda4268f345686bcfc6abecc6c3255f6b9d810341df2ca"
    )
    assert _sha256(
        ROOT / "docs/a_share_three_day_walkforward_campaign_101_report.md"
    ) == ("59f770921a857c98bbea1120c0ce60026ba0afd287b581f435470fc25baccda3")
    assert (
        _sha256(ROOT / "data/experiments/short_horizon/three_day_research_report.md")
        == "8cf4b0e1f923a3445bd73cab0ade595e442908a6ed35fb6dac62b5839bebe594"
    )
    assert (
        _sha256(ROOT / "data/experiments/short_horizon/current_research_report.md")
        == "35cb2b46ecf6868890d2bba10f04e371926496ffa24faaf316815481223c0116"
    )


def test_v3_preserves_science_and_records_only_test_scope_accounting() -> None:
    result = _load(RESULT)
    terminal = result["terminal_result"]
    assert result["supersedes_without_rewriting"]["scientific_result_changed"] is False
    assert terminal["development_survivor_count"] == 0
    assert terminal["development_aggregate_20bp_return"] == -0.21717077405952845
    assert terminal["stress_2024_2025_opened"] is False
    assert (
        result["research_boundary"][
            "formula_factor_values_folds_cost_gates_metrics_or_survivors_changed_by_v3"
        ]
        is False
    )
    assert result["research_boundary"]["additional_research_values_read_by_v3"] is False


def test_v57_preserves_exact_133_and_130_orders() -> None:
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


def test_effective_accounting_records_consumed_recovery_scope_once() -> None:
    ledger = _load(LEDGER)
    assert ledger["campaign101_attempt_count"] == 21
    assert ledger["campaign101_ledger_entry_count"] == 21
    assert (
        ledger["campaign101_infrastructure_implementation_or_recording_failure_count"]
        == 14
    )
    assert ledger["campaign101_return_reading_development_trial_count"] == 1
    assert ledger["campaign101_development_survivor_count"] == 0
    assert ledger["campaign101_stress_trial_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 745
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
