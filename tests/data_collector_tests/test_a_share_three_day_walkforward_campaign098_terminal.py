from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign097_features as definitions


ROOT = Path(__file__).resolve().parents[2]
TERMINAL = ROOT / (
    "docs/a_share_three_day_walkforward_campaign_098_"
    "terminal_verification_20260807.json"
)
LEDGER = ROOT / (
    "data/experiments/short_horizon/historical_walkforward/campaign_098/"
    "research_attempt_ledger_v6.json"
)
POLICY = ROOT / (
    "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_"
    "policy_v47_20260807.json"
)
TRIAL_LEDGER = ROOT / (
    "data/experiments/short_horizon/historical_walkforward/campaign_098/"
    "walkforward/trial_ledger.json"
)
SURVIVORS = ROOT / (
    "data/experiments/short_horizon/historical_walkforward/campaign_098/"
    "walkforward/development_survivors.json"
)
STRESS = ROOT / (
    "data/experiments/short_horizon/historical_walkforward/campaign_098/"
    "walkforward/exposed_stress_consumption_record.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_terminal_scientific_result_and_stress_boundary() -> None:
    terminal = _load(TERMINAL)
    assert terminal["status"] == (
        "verified_terminal_zero_development_survivors_stress_not_opened"
    )
    assert terminal["factor"] == "intraday_range_clock_variance_240m"
    no_return = terminal["no_return_admission"]
    assert no_return["numeric_comparison_count"] == 126
    assert no_return["all_numeric_comparisons_passed"] is True
    assert no_return["maximum_absolute_median_daily_rank_correlation"] == (
        0.4920234896112269
    )
    decision = terminal["development"]["survivor_decision"]
    assert decision["selected_survivor_count"] == 0
    assert decision["development_survivor_gate_passed"] is False
    assert set(decision["rejection_reasons"]) == {
        "insufficient_positive_pilot_return_folds",
        "median_validation_pilot_return",
        "worst_validation_normalized_drawdown",
        "nonpositive_development_aggregate_20bp_return",
    }
    assert terminal["exposed_stress"]["stress_interval_opened"] is False
    assert terminal["exposed_stress"]["stress_return_fields_read"] is False


def test_engine_outputs_are_exact_and_contain_one_complete_trial() -> None:
    assert _sha256(TRIAL_LEDGER) == (
        "e6d99116a34c1f0823334281962ff320872a77cc4d1506fa8080a43478e80f58"
    )
    assert _sha256(SURVIVORS) == (
        "b9c337e5bdcc06918cd541a5ba83fd3605ee67865e004bd5c72dc08f4f740946"
    )
    assert _sha256(STRESS) == (
        "acd016e4644f69f547a5f4d1d26e21378f70af38503bc1dfcd919405290cede3"
    )
    trial = _load(TRIAL_LEDGER)
    assert len(trial["entries"]) == 1
    assert trial["entries"][0]["trial_id"] == (
        "wf098_intraday_range_clock_variance_240m_single_higher"
    )
    assert _load(SURVIVORS)["selected_survivor_count"] == 0
    stress = _load(STRESS)
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_return_fields_read"] is False


def test_final_attempt_accounting_preserves_every_failure() -> None:
    assert _sha256(LEDGER) == (
        "f9f1ed8da63290be37fac8b6c43a76b7e703a8b8bb934792ea3d57decab37d24"
    )
    ledger = _load(LEDGER)
    assert ledger["supersedes_without_rewriting"]["preserved_attempt_count"] == 12
    assert [entry["ordinal"] for entry in ledger["entries_appended"]] == [16]
    assert ledger["campaign098_attempt_count"] == 13
    assert ledger["campaign098_ledger_entry_count"] == 16
    assert (
        ledger["campaign098_infrastructure_implementation_or_recording_failure_count"]
        == 12
    )
    assert ledger["campaign098_return_reading_development_trial_count"] == 1
    assert ledger["campaign098_development_survivor_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 692
    assert ledger["cumulative_return_reading_development_trial_count"] == 293


def test_v47_complete_and_numeric_orders_are_exact() -> None:
    assert _sha256(POLICY) == (
        "1f528805f5b6518acd96f2427544bf7448e109390d1ab37da39098bbb9661981"
    )
    policy = _load(POLICY)
    campaign097 = {
        "name": "intraday_market_range_profile_synchronization_240m",
        "score_direction": "higher",
    }
    campaign098 = {
        "name": "intraday_range_clock_variance_240m",
        "score_direction": "higher",
    }
    complete = definitions.reconstruct_complete_definitions() + [
        campaign097,
        campaign098,
    ]
    numeric = definitions.reconstruct_comparisons() + [campaign097, campaign098]
    complete_policy = policy["complete_historical_feature_library"]
    numeric_policy = policy["numerical_comparator_eligibility"]
    assert len(complete) == complete_policy["factor_definition_count"] == 130
    assert definitions._order_digest(complete) == complete_policy["order_sha256"]
    assert len(numeric) == numeric_policy["eligible_numeric_comparator_count"] == 127
    assert definitions._order_digest(numeric) == (
        numeric_policy["eligible_numeric_comparator_order_sha256"]
    )
    last = numeric_policy["last_comparator"]
    assert last["sessions_with_at_least_50_finite_names"] == 1623
    assert last["numeric_comparator_eligible_for_campaign099"] is True


def test_reports_and_candidate49_boundaries_are_current() -> None:
    for relative in (
        "docs/a_share_three_day_walkforward_campaign_098_report.md",
        "data/experiments/short_horizon/three_day_research_report.md",
        "data/experiments/short_horizon/current_research_report.md",
        "docs/a_share_data_pipeline.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "Campaign098" in text
        assert "692" in text
        assert "293" in text

    signal = ROOT / (
        "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    )
    execution = ROOT / (
        "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    )
    assert _sha256(signal) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha256(execution) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert _load(signal)["entries"] == []
    assert _load(execution)["entries"] == []
