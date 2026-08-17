from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign096_features_v2 as c96


ROOT = c96.REPO_ROOT
AUDIT = ROOT / (
    "data/experiments/short_horizon/historical_walkforward/campaign_096/"
    "no_return/20260807T043442Z_campaign096_no_return_audit.json"
)
LEDGER = ROOT / (
    "data/experiments/short_horizon/historical_walkforward/campaign_096/"
    "research_attempt_ledger_v1.json"
)
POLICY = ROOT / (
    "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_"
    "policy_v40_20260807.json"
)
RECORD = ROOT / "docs/a_share_three_day_walkforward_campaign_096_research_record.json"
EFFICIENCY = ROOT / (
    "docs/a_share_three_day_walkforward_campaign_096_"
    "postresult_support_equivalence_efficiency_audit_20260807.json"
)
FREEZE = ROOT / (
    "docs/a_share_three_day_walkforward_campaign_096_"
    "terminal_completion_freeze_20260807.json"
)
SNAPSHOT = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign096_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign096_feature_library_v1/snapshot_manifest.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_campaign096_stops_on_coverage_before_comparisons_or_returns() -> None:
    audit = _load(AUDIT)
    coverage = audit["coverage_and_capacity"][c96.FACTOR_NAME]
    assert audit["status"] == (
        "completed_zero_admissible_factors_stop_before_historical_daily_prices_or_returns"
    )
    assert coverage["gate_passed_before_comparison_values"] is False
    assert coverage["median_coverage"] == 0.9231861259965655
    assert coverage["p05_coverage"] == 0.8075504413619168
    assert coverage["eligible_names_p05"] == 127.55000000000001
    assert coverage["potential_non_overlapping_three_session_cohorts"] == 538
    assert coverage["observed_cohort_years"] == list(range(2019, 2026))
    assert audit["uniqueness"][c96.FACTOR_NAME]["comparison_factor_count"] == 0
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False
    assert audit["training_or_model_fitting_performed"] is False
    assert audit["current_scoring_selection_sizing_or_orders_performed"] is False


def test_campaign096_attempt_accounting_is_additive() -> None:
    ledger = _load(LEDGER)
    assert ledger["append_only"] is True
    assert len(ledger["entries"]) == ledger["campaign096_ledger_entry_count"] == 6
    assert ledger["campaign096_attempt_count"] == 6
    assert ledger["campaign096_infrastructure_or_implementation_failure_count"] == 5
    assert ledger["campaign096_complete_factor_attempt_count"] == 1
    assert ledger["campaign096_return_reading_development_trial_count"] == 0
    assert ledger["campaign096_development_survivor_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 665
    assert ledger["cumulative_return_reading_development_trial_count"] == 291
    assert [entry["ordinal"] for entry in ledger["entries"]] == list(range(1, 7))
    assert (
        sum(entry["research_attempt_count_increment"] for entry in ledger["entries"])
        == 6
    )


def test_v40_appends_complete_and_numeric_orders_and_freezes_support_gate() -> None:
    policy = _load(POLICY)
    complete = policy["complete_historical_feature_library"]
    numeric = policy["numerical_comparator_eligibility"]
    assert complete["factor_definition_count"] == 128
    assert complete["order_sha256"] == (
        "9380287d8339113cb01fa99670c77078f9be82b7463c06c1e7debb92b1add48b"
    )
    assert complete["last_definition"] == {
        "name": c96.FACTOR_NAME,
        "score_direction": "higher",
    }
    assert numeric["eligible_numeric_comparator_count"] == 125
    assert numeric["eligible_numeric_comparator_order_sha256"] == (
        "50a737e640cac8e063aab8be0b483a6d9be87d0e5ddd1e1395e625ab371a4cae"
    )
    assert numeric["last_comparator"]["name"] == c96.FACTOR_NAME
    assert numeric["last_comparator"]["sessions_with_at_least_50_finite_names"] == 1622
    assert (
        numeric["last_comparator"]["numeric_comparator_eligible_for_campaign097"]
        is True
    )
    support_gate = policy[
        "mandatory_prevalue_support_predicate_gate_for_campaign097_and_later"
    ]
    assert support_gate["required"] is True
    assert (
        support_gate[
            "known_campaign086_campaign096_support_equivalence_must_be_challenged"
        ]
        is True
    )
    assert (
        support_gate[
            "campaign096_may_be_rerun_with_a_different_norm_direction_threshold_subset_filter_or_support_repair"
        ]
        is False
    )


def test_support_equivalence_and_candidate49_boundaries_are_preserved() -> None:
    efficiency = _load(EFFICIENCY)
    evidence = efficiency["evidence"]
    assert evidence["campaign086_candidate_eligible_rows"] == 1_193_690
    assert evidence["campaign096_candidate_eligible_rows"] == 1_193_690
    assert (
        evidence["campaign086_median_coverage"]
        == evidence["campaign096_median_coverage"]
    )
    assert evidence["campaign086_p05_coverage"] == evidence["campaign096_p05_coverage"]
    record = _load(RECORD)
    assert record["efficiency_finding"] == {
        "support_predicate_matches_campaign086_terminal_coverage_failure": True,
        "coverage_failure_predictable_before_values": True,
        "candidate_selection_efficiency_failure": True,
        "scientific_return_conclusion": "none; no return was read",
        "mandatory_future_rule": (
            "Reject before values any candidate whose exact support predicate is "
            "identical to or no broader than a known terminal coverage failure "
            "under the same universe and thresholds."
        ),
    }
    candidate49 = record["candidate49_future_only_layer"]
    signal = ROOT / (
        "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    )
    execution = ROOT / (
        "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    )
    assert _sha256(signal) == candidate49["signal_ledger_sha256"]
    assert _sha256(execution) == candidate49["execution_ledger_sha256"]
    assert candidate49["signal_ledger_entries"] == 0
    assert candidate49["execution_ledger_entries"] == 0
    assert candidate49["historical_backfill_performed"] is False
    assert candidate49["provider_request_issued"] is False
    assert candidate49["second_prospective_candidate_created"] is False


def test_terminal_freeze_bindings_reports_and_snapshot_are_exact() -> None:
    assert _sha256(AUDIT) == (
        "ce5715ae81d7252e7bc3d7549fd1c069c3d1e19156c1a5c25f4802790ce2fea1"
    )
    assert _sha256(LEDGER) == (
        "b3fe17e20cfe4cf8d07e1d41f99a1c786191188d32b53f34a800f5998ead4063"
    )
    assert _sha256(POLICY) == (
        "e8fc39da2d29ac91e094c239186d8e9a561ef53a8ee44e3f7f2b176e9103e8ba"
    )
    assert _sha256(RECORD) == (
        "c41e34d78cc5c5da39f5e97ea8e15f6e5fcf40aa6f930ae83eb49135ae9e65aa"
    )
    assert _sha256(FREEZE) == (
        "9254b853c41eca6688320f3987feeb2b3cecf7d1b3398878be5f26195b8a9d1e"
    )
    assert bindings.validate_record(RECORD)["all_bindings_passed"] is True
    assert bindings.validate_record(POLICY)["all_bindings_passed"] is True
    assert bindings.validate_record(FREEZE)["all_bindings_passed"] is True
    freeze = _load(FREEZE)
    for key in (
        "campaign_report",
        "unified_report",
        "current_report",
        "data_pipeline_documentation",
    ):
        report = ROOT / freeze[key]["path"]
        assert _sha256(report) == freeze[key]["sha256"]
    assert _sha256(SNAPSHOT) == (
        "1b205f1b6d3b28248b765860b8cf0e4aecee07f960fa535402e316ba13c39a3a"
    )
    assert c96.verify_snapshot_files(SNAPSHOT) == {
        "status": "verified",
        "dataset_sha256": (
            "67106bd4f5d4382b770cb79355c27ea4d8ca179296841b7bd9fa2963a46e09f3"
        ),
        "partitions": 7,
        "rows": 1_331_759,
        "eligible_rows": 1_193_690,
        "comparison_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }
