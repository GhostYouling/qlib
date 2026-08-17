from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign100_features as c100
from scripts import a_share_three_day_walkforward_campaign101_features as c101

ROOT = Path(__file__).resolve().parents[2]
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_101_terminal_result_binding_v4_20260807.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_101/research_attempt_ledger_v16.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v58_20260807.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_effective_terminal_artifact_hashes_are_exact() -> None:
    assert _sha256(RESULT) == (
        "1de051b943c775fe09b3e44d2203d1922d76c1f282f9cddca9062c09362506fc"
    )
    assert _sha256(LEDGER) == (
        "541af125d90fffd06f161238cff822ed607ade6ee23605ed7c96a1dd5570d6df"
    )
    assert _sha256(POLICY) == (
        "45571a0d525d3c7132f6392914dd80b51ec179b51d21e548102292ec70674edc"
    )
    survivors = (
        ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_101/walkforward/development_survivors.json"
    )
    assert _sha256(survivors) == (
        "a9a704c37e6975f4cf54f7e245d0d7ad689fda3f224539b81979c1cf56303e1c"
    )


def test_science_is_terminal_zero_survivors_and_stress_closed() -> None:
    result = _load(RESULT)
    terminal = result["terminal_result"]
    assert result["supersedes_without_rewriting"]["scientific_result_changed"] is False
    assert terminal["numeric_comparison_pass_count"] == 129
    assert terminal["numeric_comparison_count"] == 129
    assert terminal["development_trial_count"] == 1
    assert terminal["positive_rank_ic_fold_count"] == 0
    assert terminal["positive_normalized_return_fold_count"] == 0
    assert terminal["positive_pilot_10bp_return_fold_count"] == 0
    assert terminal["development_aggregate_20bp_return"] == -0.21717077405952845
    assert terminal["development_survivor_count"] == 0
    assert terminal["stress_2024_2025_opened"] is False
    assert terminal["stress_2024_2025_return_fields_read"] is False


def test_v58_preserves_exact_133_definition_and_130_numeric_orders() -> None:
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


def test_final_accounting_and_reports_are_current() -> None:
    ledger = _load(LEDGER)
    assert ledger["campaign101_attempt_count"] == 22
    assert ledger["campaign101_ledger_entry_count"] == 22
    assert (
        ledger["campaign101_infrastructure_implementation_or_recording_failure_count"]
        == 15
    )
    assert ledger["campaign101_return_reading_development_trial_count"] == 1
    assert ledger["campaign101_development_survivor_count"] == 0
    assert ledger["campaign101_stress_trial_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 746
    assert ledger["cumulative_return_reading_development_trial_count"] == 295
    for path in (
        ROOT / "docs/a_share_three_day_walkforward_campaign_101_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
        ROOT / "data/experiments/short_horizon/current_research_report.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "22 次尝试" in text
        assert "v58" in text
        assert "133/130" in text


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
