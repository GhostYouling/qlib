from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign097 as campaign097


ROOT = Path(__file__).resolve().parents[2]
TERMINAL = ROOT / (
    "docs/a_share_three_day_walkforward_campaign_097_"
    "terminal_verification_20260807.json"
)
TRIAL_LEDGER = ROOT / (
    "data/experiments/short_horizon/historical_walkforward/campaign_097/"
    "walkforward/trial_ledger.json"
)
SURVIVORS = ROOT / (
    "data/experiments/short_horizon/historical_walkforward/campaign_097/"
    "walkforward/development_survivors.json"
)
STRESS = ROOT / (
    "data/experiments/short_horizon/historical_walkforward/campaign_097/"
    "walkforward/exposed_stress_consumption_record.json"
)
RESEARCH_LEDGER = ROOT / (
    "data/experiments/short_horizon/historical_walkforward/campaign_097/"
    "research_attempt_ledger_v2.json"
)
CAMPAIGN_REPORT = ROOT / (
    "data/experiments/short_horizon/historical_walkforward/campaign_097/"
    "walkforward/campaign_report.json"
)
SIGNAL_LEDGER = ROOT / (
    "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER = ROOT / (
    "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_terminal_binding_chain_and_runtime_status_are_exact() -> None:
    assert _sha256(TERMINAL) == (
        "e2bdfaf91a58d58de27a37aaeb578ac9c6452cda7a2c9774b89a675f36e10996"
    )
    validation = bindings.validate_record(TERMINAL)
    assert validation["all_bindings_passed"] is True
    assert validation["binding_count"] == validation["passed_binding_count"] == 11

    args = campaign097.parser().parse_args(["status"])
    status = campaign097.status(args)
    assert status == {
        "campaign_id": "a_share_three_day_walkforward_campaign_097",
        "campaign_sha256": (
            "1184e05bcfaaecb3767fa0df77afc20e3e8425ab88fb0e374adf26164a6d65fd"
        ),
        "expected_trial_count": 1,
        "candidate49_historical_return_read": False,
        "current_scoring_selection_sizing_or_orders_allowed": False,
        "ledger_entry_count": 3,
        "ledger_chain_tip_sha256": (
            "8ae033cb67fbc27606d268d65eaa395c6416c8234cc0851a74e5494e7b24dd63"
        ),
        "selected_survivor_count": 0,
        "stress_intent_exists": False,
        "stress_record_exists": True,
        "stress_status": "not_opened_zero_development_survivors",
    }


def test_no_return_admission_and_compact_snapshot_are_exact() -> None:
    terminal = _load(TERMINAL)
    admission = terminal["no_return_admission"]
    assert admission["quality_listing_eligible_rows"] == 1_331_759
    assert admission["candidate_eligible_rows"] == 1_328_449
    assert admission["median_coverage"] == 0.9985369414262841
    assert admission["p05_coverage"] == 0.9935483870967742
    assert admission["numeric_comparison_count"] == 125
    assert admission["all_numeric_comparisons_passed"] is True
    assert admission["maximum_absolute_median_daily_rank_correlation"] == (
        0.6841082841394884
    )
    assert (
        admission[
            "historical_daily_price_or_forward_return_values_read_before_admission"
        ]
        is False
    )

    snapshot = terminal["compact_feature_snapshot"]["manifest"]
    assert snapshot["partitions"] == 7
    assert snapshot["rows"] == 1_331_759
    assert snapshot["eligible_rows"] == 1_328_449
    assert snapshot["dataset_sha256"] == (
        "dfdeda35efb8e443e4f33a6ab217032ec2ba6793270f8eb7fcf36d9494f7bf97"
    )


def test_append_only_development_ledger_and_metrics_are_exact() -> None:
    ledger = _load(TRIAL_LEDGER)
    entries = ledger["entries"]
    assert [entry["phase"] for entry in entries] == [
        "infrastructure_failure",
        "infrastructure_failure",
        "development_walkforward_2019_2023",
    ]
    assert [entry["ordinal"] for entry in entries] == [1, 2, 3]
    assert (
        ledger["chain_tip_sha256"]
        == entries[-1]["entry_sha256"]
        == ("8ae033cb67fbc27606d268d65eaa395c6416c8234cc0851a74e5494e7b24dd63")
    )
    trial = entries[-1]
    assert trial["trial_id"] == (
        "wf097_intraday_market_range_profile_synchronization_240m_single_higher"
    )
    assert [
        fold["association"]["mean_rank_ic"] for fold in trial["validation_metrics"]
    ] == [
        -0.011442805633971903,
        -0.016383618700888527,
        -0.016474405032354214,
    ]
    aggregate = trial["development_aggregate_metrics"]
    assert aggregate["association"]["mean_rank_ic"] == -0.0067861268185640975
    assert aggregate["normalized_execution"]["net_cumulative_return"] == (
        0.8771658219657235
    )
    assert aggregate["pilot_execution_primary_10bp"]["net_cumulative_return"] == (
        0.031100502198090796
    )
    assert aggregate["pilot_slippage_sensitivity"]["0.0020"][
        "net_cumulative_return"
    ] == (-0.085855546438384)


def test_zero_survivors_keep_exposed_stress_closed() -> None:
    survivors = _load(SURVIVORS)
    assert survivors["selected_survivor_count"] == 0
    assert survivors["selected_exposed_stress_survivor_trial_ids"] == []
    decision = survivors["trial_decisions"][0]
    assert decision["operationally_admissible"] is True
    assert decision["validation_quality_gate_passed"] is False
    assert decision["development_survivor_gate_passed"] is False
    assert decision["positive_mean_rank_ic_fold_count"] == 0
    assert decision["positive_normalized_return_fold_count"] == 2
    assert decision["positive_pilot_return_fold_count"] == 1
    assert decision["validation_quality_rejection_reasons"] == [
        "insufficient_positive_ic_folds",
        "median_validation_mean_rank_ic",
        "insufficient_positive_pilot_return_folds",
        "median_validation_pilot_return",
        "worst_validation_normalized_drawdown",
        "nonpositive_development_aggregate_20bp_return",
    ]

    stress = _load(STRESS)
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["selected_survivor_count"] == 0
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    assert stress["candidate49_historical_return_read"] is False


def test_attempt_accounting_includes_failures_omitted_by_generated_report() -> None:
    ledger = _load(RESEARCH_LEDGER)
    assert ledger["campaign097_attempt_count"] == 10
    assert ledger["campaign097_ledger_entry_count"] == 13
    assert ledger["campaign097_infrastructure_or_implementation_failure_count"] == 9
    assert ledger["campaign097_complete_factor_attempt_count"] == 1
    assert ledger["campaign097_return_reading_development_trial_count"] == 1
    assert ledger["campaign097_development_survivor_count"] == 0
    assert ledger["campaign097_stress_trial_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 676
    assert ledger["cumulative_return_reading_development_trial_count"] == 292
    assert [entry["ordinal"] for entry in ledger["entries_appended"]] == [
        10,
        11,
        12,
        13,
    ]

    generated = _load(CAMPAIGN_REPORT)
    assert generated["infrastructure_failure_count"] == 0
    terminal = _load(TERMINAL)
    discrepancy = terminal["generated_campaign_report"]
    assert discrepancy["inherited_infrastructure_failure_count_field"] == 0
    assert (
        discrepancy["observed_internal_trial_ledger_infrastructure_failure_count"] == 2
    )
    assert discrepancy["authoritative_failure_accounting_source"] == (
        "research_attempt_ledger_v2"
    )
    assert discrepancy["generated_report_rewritten"] is False


def test_candidate49_and_current_action_boundaries_remain_closed() -> None:
    terminal = _load(TERMINAL)
    candidate49 = terminal["candidate49"]
    assert (
        _sha256(SIGNAL_LEDGER)
        == candidate49["signal_ledger_sha256"]
        == ("5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79")
    )
    assert (
        _sha256(EXECUTION_LEDGER)
        == candidate49["execution_ledger_sha256"]
        == ("d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f")
    )
    assert _load(SIGNAL_LEDGER)["entries"] == []
    assert _load(EXECUTION_LEDGER)["entries"] == []
    assert candidate49["historical_return_read"] is False
    assert candidate49["ledgers_changed"] is False
    assert candidate49["remains_only_active_prospective_candidate"] is True
    actions = terminal["terminal_actions"]
    assert actions["campaign097_factor_terminated"] is True
    assert (
        actions["campaign097_may_be_rescued_reweighted_or_combined_post_result"]
        is False
    )
    assert (
        actions[
            "current_scoring_selection_sizing_orders_or_second_prospective_candidate_created"
        ]
        is False
    )
    assert actions["provider_request_issued"] is False
