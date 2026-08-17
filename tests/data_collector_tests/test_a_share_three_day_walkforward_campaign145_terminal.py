from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign145_features as c145


ROOT = Path(__file__).resolve().parents[2]
SCOUTING = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_145_concept_scouting_20260814.json"
)
PREREGISTRATION = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_145_no_return_preregistration_20260814.json"
)
RECOVERY = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_145_snapshot_recovery_verification_20260814.json"
)
COVERAGE = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_145/coverage/campaign145_coverage_audit.json"
)
LEDGER_V1 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_145/research_attempt_ledger_v1.json"
)
LEDGER_V2 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_145/research_attempt_ledger_v2.json"
)
LEDGER_V3 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_145/research_attempt_ledger_v3.json"
)
LEDGER_V4 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_145/research_attempt_ledger_v4.json"
)
TERMINAL_V1 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_145_terminal_result_20260814.json"
)
TERMINAL_V2 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_145_terminal_result_v2_20260814.json"
)
TERMINAL_V3 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_145_terminal_result_v3_20260814.json"
)
TERMINAL_V4 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_145_terminal_result_v4_20260814.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v194_20260814.json"
)
CURRENT_REPORT = ROOT / "data/experiments/short_horizon/current_research_report.md"
THREE_DAY_REPORT = ROOT / "data/experiments/short_horizon/three_day_research_report.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _entry_hash(entry: dict, previous: str) -> str:
    payload = "|".join(
        (
            "campaign145",
            entry["attempt_id"],
            previous,
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_campaign145_finite_catalog_selects_one_prevalue_frozen_factor() -> None:
    scouting = _load(SCOUTING)
    catalog = scouting["finite_prevalue_concept_catalog"]
    assert len(catalog) == 6
    assert [item["catalog_id"] for item in catalog] == [
        f"c145_{index:02d}" for index in range(1, 7)
    ]
    assert scouting["selection"]["selected_candidate_count"] == 1
    assert scouting["selection"]["selected_catalog_id"] == "c145_01"
    preregistration = _load(PREREGISTRATION)
    assert preregistration["candidate"]["name"] == c145.FACTOR_NAME
    assert preregistration["candidate"]["direction"] == "higher"
    assert (
        preregistration["research_boundary"][
            "campaign145_candidate_values_computed_or_read_before_freeze"
        ]
        is False
    )


def test_campaign145_snapshot_recovery_is_exact_and_nonmutating() -> None:
    recovery = _load(RECOVERY)
    snapshot = recovery["snapshot_manifest"]
    assert snapshot["partitions"] == 33_015
    assert snapshot["rows"] == 7_724_498
    assert snapshot["eligible_rows"] == 3_954_911
    assert (
        snapshot["dataset_sha256"]
        == "d7cde236c58871314718febfb72f4e72d2cb6bab6729ee0f979b335e92a2acc0"
    )
    correction = recovery["known_header_correction"]
    assert correction["effective_verified_range"] == {c145.FACTOR_NAME: [-1.0, 1.0]}
    assert correction["snapshot_manifest_or_partition_rewritten"] is False
    assert all(
        value is True
        for key, value in recovery["verification"].items()
        if key != "exit_code"
    )


def test_campaign145_coverage_failure_stops_before_comparators_and_returns() -> None:
    coverage = _load(COVERAGE)
    metrics = coverage["coverage_and_variation"]
    assert coverage["status"] == "coverage_failed_terminal_before_all_comparator_values"
    assert metrics["median_daily_coverage"] == 0.5246269205322356
    assert metrics["p05_daily_coverage"] == 0.20608206686930092
    assert metrics["eligible_names_p05"] == 49.0
    assert metrics["cross_sectional_variation_gate_passed"] is True
    assert metrics["gate_passed_before_comparator_values"] is False
    assert coverage["comparator_values_read"] is False
    assert coverage["numeric_comparator_count_read"] == 0
    assert coverage["historical_forward_return_fields_read"] is False
    assert coverage["stress_2024_2025_opened"] is False


def test_campaign145_library_appends_definition_but_not_numeric_series() -> None:
    policy = _load(POLICY)
    assert len(c145.reconstruct_complete_definitions()) == 154
    assert c145.COMPLETE_DEFINITION_ORDER_SHA256 == (
        "dcea4c75bb9194ea2e522d803409e4005cf0185fe87c84f6f9810dbe51de2f75"
    )
    assert len(c145.reconstruct_comparisons()) == 141
    assert c145.NUMERIC_COMPARATOR_ORDER_SHA256 == (
        "ec1aebcb939ad516c58037a36a4aaadd4ad8b2abbd3c884705895c58da85a2ee"
    )
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"] == 154
    )
    assert (
        policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"]
        == 141
    )
    assert (
        policy["numerical_comparator_eligibility"][
            "campaign145_numeric_series_appended"
        ]
        is False
    )


def test_campaign145_append_only_attempt_chain_and_accounting() -> None:
    ledger = _load(LEDGER_V1)
    previous = ledger["chain_genesis"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry, previous)
        evidence = entry.get("evidence")
        if evidence:
            assert _sha(ROOT / evidence["path"]) == evidence["sha256"]
        previous = entry["entry_sha256"]
    assert previous == ledger["chain_tip_sha256"]

    delta = _load(LEDGER_V2)
    assert delta["authoritative_predecessor"]["sha256"] == _sha(LEDGER_V1)
    for entry in delta["entries"]:
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry, previous)
        evidence = ROOT / entry["evidence"]["path"]
        assert _sha(evidence) == entry["evidence"]["sha256"]
        previous = entry["entry_sha256"]
    assert previous == delta["chain_tip_sha256"]
    latest = _load(LEDGER_V3)
    assert latest["authoritative_predecessor"]["sha256"] == _sha(LEDGER_V2)
    for entry in latest["entries"]:
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry, previous)
        evidence = ROOT / entry["evidence"]["path"]
        assert _sha(evidence) == entry["evidence"]["sha256"]
        previous = entry["entry_sha256"]
    assert previous == latest["chain_tip_sha256"]
    effective = _load(LEDGER_V4)
    assert effective["authoritative_predecessor"]["sha256"] == _sha(LEDGER_V3)
    for entry in effective["entries"]:
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry, previous)
        evidence = ROOT / entry["evidence"]["path"]
        assert _sha(evidence) == entry["evidence"]["sha256"]
        previous = entry["entry_sha256"]
    assert previous == effective["chain_tip_sha256"]
    assert effective["effective_attempt_count"] == 11
    assert effective["effective_infrastructure_failure_attempt_count"] == 10
    assert effective["effective_return_reading_development_trial_count"] == 0
    assert effective["cumulative_historical_research_attempt_count"] == 1251
    assert effective["cumulative_return_reading_development_trial_count"] == 313


def test_campaign145_terminal_bindings_reports_and_candidate49_boundary() -> None:
    for path in (
        SCOUTING,
        PREREGISTRATION,
        RECOVERY,
        COVERAGE,
        LEDGER_V1,
        LEDGER_V2,
        LEDGER_V3,
        LEDGER_V4,
        TERMINAL_V1,
        TERMINAL_V2,
        TERMINAL_V3,
        TERMINAL_V4,
        POLICY,
    ):
        report = bindings.validate_record(path)
        assert report["all_bindings_passed"] is True, (path, report)
    terminal = _load(TERMINAL_V4)
    assert terminal["terminal_scientific_result"]["coverage_gate_passed"] is False
    assert terminal["candidate49"]["signal_entries"] == 0
    assert terminal["candidate49"]["execution_entries"] == 0
    assert terminal["candidate49"]["ledgers_changed"] is False
    heading = "## Campaign145 分钟收益—金额累积路径面积覆盖率终止"
    assert CURRENT_REPORT.read_text(encoding="utf-8").count(heading) == 1
    assert THREE_DAY_REPORT.read_text(encoding="utf-8").count(heading) == 1
