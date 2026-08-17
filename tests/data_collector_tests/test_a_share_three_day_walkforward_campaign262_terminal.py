from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TERMINAL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_262_terminal_result_v4_20260816.json"
)
POLICY = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v407_20260816.json"
)
LEDGER_BASE = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_262/research_attempt_ledger_v3.json"
)
LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_262/research_attempt_ledger_v4.json"
)
FAILED_LEDGER_V1 = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_262/research_attempt_ledger_v1.json"
)
COVERAGE = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_262/coverage/campaign262_coverage_audit.json"
)
UNIQUENESS = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_262/uniqueness/campaign262_ordered_uniqueness_audit.json"
)
SIGNAL = (
    REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION = (
    REPO_ROOT
    / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)
REPORTS = (
    REPO_ROOT / "data/experiments/short_horizon/current_research_report.md",
    REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md",
)


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _entry_hash(entry: dict) -> str:
    body = {key: value for key, value in entry.items() if key != "entry_sha256"}
    payload = json.dumps(
        body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def test_terminal_and_policy_bind_current_campaign262_artifacts() -> None:
    terminal = _load(TERMINAL)
    policy = _load(POLICY)
    assert (
        _sha256(TERMINAL)
        == "b762fe8562a1c80a5e7b0825220c507a9c552fad696956bb74d99c5b848dda5a"
    )
    assert (
        _sha256(POLICY)
        == "62dd56694334338481c5341c00464f76ce166859db3e48d1c73fc2f3c8e431fa"
    )
    assert policy["version"] == 407
    assert policy["authoritative_inputs"]["campaign262_terminal_result_v4"][
        "sha256"
    ] == _sha256(TERMINAL)
    assert terminal["authoritative_inputs"]["campaign262_attempt_ledger_v4"][
        "sha256"
    ] == _sha256(LEDGER)
    for item in terminal["authoritative_inputs"].values():
        assert _sha256(REPO_ROOT / item["path"]) == item["sha256"]


def test_terminal_science_stops_before_returns() -> None:
    terminal = _load(TERMINAL)
    science = terminal["scientific_result"]
    assert science["factor"] == "intraday_amount_schedule_uniformity_240m"
    assert science["direction"] == "higher"
    assert science["coverage_gate_passed"] is True
    assert science["numeric_comparison_count"] == 142
    assert science["numeric_uniqueness_passed"] is False
    assert [item["name"] for item in science["failing_comparators"]] == [
        "intraday_amount_center_of_mass_240m"
    ]
    assert (
        science["failing_comparators"][0]["absolute_median_daily_rank_correlation"]
        == 0.8906904661969348
    )
    assert science["other_comparators_passed"] == 141
    assert science["development_trial_count"] == 0
    assert science["stress_trial_count_2024_2025"] == 0
    assert science["selected_factor_count"] == 0
    assert science["retry_or_rescue_allowed"] is False
    assert (
        terminal["research_boundary"][
            "historical_daily_price_or_forward_return_values_read"
        ]
        is False
    )


def test_coverage_and_all_uniqueness_results_are_exact() -> None:
    coverage = _load(COVERAGE)
    uniqueness = _load(UNIQUENESS)
    gate = coverage["coverage_and_variation"]
    assert gate["gate_passed_before_comparator_values"] is True
    assert gate["candidate_eligible_rows"] == 1_330_171
    assert gate["median_daily_coverage"] == 0.9994517542211769
    assert gate["p05_daily_coverage"] == 0.9956886515772271
    assert len(uniqueness["comparisons"]) == 142
    assert uniqueness["all_142_results_recorded_without_early_stop"] is True
    failed = [item for item in uniqueness["comparisons"] if not item["gate_passed"]]
    assert [item["comparison_factor"] for item in failed] == [
        "intraday_amount_center_of_mass_240m"
    ]
    assert uniqueness["historical_daily_price_or_forward_return_values_read"] is False
    assert uniqueness["stress_2024_2025_return_values_opened"] is False


def test_append_only_recovery_ledger_v3_chain() -> None:
    base = _load(LEDGER_BASE)
    previous = base["authoritative_predecessor"]["chain_tip_sha256"]
    for ordinal, entry in enumerate(base["entries"], 1):
        assert entry["ordinal"] == ordinal
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        previous = entry["entry_sha256"]
    assert previous == base["chain_tip_sha256"]
    ledger = _load(LEDGER)
    assert ledger["authoritative_predecessor"]["sha256"] == _sha256(LEDGER_BASE)
    for ordinal, entry in enumerate(ledger["delta_entries"], 23):
        assert entry["ordinal"] == ordinal
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        previous = entry["entry_sha256"]
    assert previous == ledger["chain_tip_sha256"]
    assert ledger["effective_entry_count"] == 25
    assert ledger["effective_infrastructure_failure_attempt_count"] == 18
    assert ledger["effective_prevalue_scientific_attempt_count"] == 7
    assert ledger["effective_complete_factor_attempt_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 2563
    assert ledger["cumulative_return_reading_development_trial_count"] == 314
    assert _load(FAILED_LEDGER_V1)["entries"] == []
    assert base["failed_lifecycle_ledgers_preserved"][0]["sha256"] == _sha256(
        FAILED_LEDGER_V1
    )


def test_library_and_candidate49_semantics_remain_frozen() -> None:
    policy = _load(POLICY)
    library = policy["complete_historical_feature_library"]
    comparison = policy["numerical_comparator_eligibility"]
    assert library["factor_definition_count"] == 161
    assert (
        library["order_sha256"]
        == "e387d2865b8957a933c522c2cd9ae890612ab45993307f97693ec73fa5288144"
    )
    assert library["campaign262_definition_appended_once"] is True
    assert comparison["eligible_numeric_comparator_count"] == 142
    assert comparison["campaign262_numeric_comparator_appended"] is False
    assert (
        comparison["order_sha256"]
        == "5d1b35fb5a0d8ac9293008db9963c4a60a94dc940c237c3ed259e5ce44f14aaf"
    )
    assert (
        _sha256(SIGNAL)
        == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert (
        _sha256(EXECUTION)
        == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert _load(SIGNAL)["entries"] == []
    assert _load(EXECUTION)["entries"] == []


def test_unified_reports_have_one_matching_campaign262_section() -> None:
    heading = "## Campaign262：成交额均匀日程数值唯一性终止"
    for path in REPORTS:
        text = path.read_text(encoding="utf-8")
        assert text.count(heading) == 1
        assert "+0.890690" in text
        assert "累计历史尝试更正为 2,563" in text
        assert "Campaign263" in text


def test_campaign263_offline_boundary_is_authorized_without_current_use() -> None:
    policy = _load(POLICY)
    assert policy["future_campaign_boundary"]["next_campaign"] == 263
    assert (
        policy["future_campaign_boundary"][
            "historical_offline_prevalue_work_may_continue_at_any_local_time"
        ]
        is True
    )
    boundary = policy["research_boundary"]
    assert boundary["provider_or_web_request_issued"] is False
    assert boundary["candidate49_plan_or_run_executed"] is False
    assert (
        boundary["current_scoring_selection_sizing_positions_or_orders_performed"]
        is False
    )
    assert boundary["investment_advice"] is False
