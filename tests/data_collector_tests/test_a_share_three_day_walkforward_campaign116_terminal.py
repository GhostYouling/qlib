from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_116/coverage/campaign116_coverage_audit.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_116/research_attempt_ledger_v8.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_116_terminal_result_20260812.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v104_20260812.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260812_campaign116_terminal_v3.json"
)
ACTIVATION = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_116_coverage_activation_binding_20260812.json"
)
FREEZE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_116_coverage_audit_implementation_freeze_20260812.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign116_terminal_artifact_hashes_are_exact() -> None:
    assert _sha256(FREEZE) == (
        "8fd52afa097ba2ec70ed9daae6883cc0233618a5e8daaf0a5f8471457a9ef257"
    )
    assert _sha256(ACTIVATION) == (
        "2b3569faccf5b2fa02cfde7139378ad7174e4495e8b56885460c8d4b82147177"
    )
    assert _sha256(AUDIT) == (
        "dd423d61211993451a6b96ec318bc0032061557ae7014ca7ca72e9d993c0591c"
    )
    assert _sha256(LEDGER) == (
        "677c43872c3e7233569478d8692287d23f553dc1aab69451adcc70aeb1a4a12b"
    )
    assert _sha256(RESULT) == (
        "5f3dd3ba3e654695f14c920a746ebd6b7897dac61e90e9b2d24cbdeb21dbb3bc"
    )
    assert _sha256(POLICY) == (
        "a9d44ce8b383a9ecb29f96b8df19ac1bc28e7cceaac8397c609be6130e4ef03b"
    )
    assert _sha256(STATE) == (
        "35f6ffe0faf838dab24a8cc9dde487f779c99be65973e14c8867059fac346eba"
    )


def test_coverage_failure_stops_before_all_comparators_and_returns() -> None:
    audit = _load(AUDIT)
    coverage = audit["coverage_and_variation"]
    assert audit["status"] == "coverage_failed_terminal_before_all_comparator_values"
    assert coverage["median_daily_coverage"] == 0.8501338090990187
    assert coverage["p05_daily_coverage"] == 0.7141794569067297
    assert coverage["eligible_names_p05"] == 121.0
    assert coverage["potential_non_overlapping_three_signal_session_cohorts"] == 539
    assert coverage["nonconstant_cross_sectional_sessions"] == 1632
    assert coverage["coverage_capacity_gate_passed"] is False
    assert coverage["cross_sectional_variation_gate_passed"] is True
    assert coverage["gate_passed_before_comparator_values"] is False
    assert audit["numeric_comparator_count_read"] == 0
    assert audit["comparator_values_read"] is False
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False
    assert audit["stress_2024_2025_opened"] is False
    assert audit["provider_request_issued"] is False
    assert audit["credential_loaded"] is False


def test_v8_ledger_preserves_terminal_result_and_records_patch_failure() -> None:
    ledger = _load(LEDGER)
    extension = ledger["extends_without_rewriting"]
    assert extension["sha256"] == (
        "958e30a06d5afd9a5cb41a58eaf88b0b9c0ce41c56d99d4e1e893f0509299bb0"
    )
    entry = ledger["entries"][0]
    payload = (
        "campaign116|"
        + entry["attempt_id"]
        + "|"
        + entry["previous_entry_sha256"]
        + "|"
        + entry["phase"]
        + "|"
        + entry["status"]
    ).encode()
    assert hashlib.sha256(payload).hexdigest() == entry["entry_sha256"]
    assert entry["research_attempt_count_increment"] == 1
    assert entry["infrastructure_failure_count_increment"] == 1
    assert entry["scientific_result_changed"] is False
    assert ledger["attempt_count"] == 7
    assert ledger["infrastructure_failure_count"] == 6
    assert ledger["complete_factor_attempt_count"] == 1
    assert ledger["return_reading_complete_development_trial_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 885
    assert ledger["cumulative_return_reading_development_trial_count"] == 302


def test_terminal_result_is_structural_not_predictive_evidence() -> None:
    result = _load(RESULT)
    interpretation = result["scientific_interpretation"]
    assert interpretation["predictive_direction_tested"] is False
    assert interpretation["numeric_uniqueness_tested"] is False
    assert interpretation["historical_return_tested"] is False
    assert interpretation["post_result_rescue_allowed"] is False
    assert result["unopened_stages"]["numeric_comparator_count_read"] == 0
    assert result["unopened_stages"]["development_trial_count"] == 0
    assert result["unopened_stages"]["stress_2024_2025_opened"] is False


def test_v104_preserves_142_definitions_and_134_comparators() -> None:
    policy = _load(POLICY)
    assert policy["campaign116_terminal_classification"]["terminal"] is True
    assert (
        policy["campaign116_terminal_classification"]["coverage_gate_passed"] is False
    )
    definitions = policy["complete_historical_feature_library"]
    comparators = policy["numerical_comparator_eligibility"]
    assert definitions["factor_definition_count"] == 142
    assert definitions["order_sha256"] == (
        "ed61b10f3acb939c10ae5759f33aafde377cc921dd99c642300603b50a4851c5"
    )
    assert comparators["eligible_numeric_comparator_count"] == 134
    assert comparators["eligible_numeric_comparator_order_sha256"] == (
        "31d788db467f558a0ac538315343090f1b3ad4cb27a26136a49ebaa88b2fdbf2"
    )
    assert comparators["campaign116_numeric_comparator_appended"] is False
    assert policy["effective_accounting"]["campaign116_attempt_count"] == 7
    assert (
        policy["effective_accounting"]["cumulative_historical_research_attempt_count"]
        == 885
    )


def test_state_preserves_candidate49_and_opens_only_campaign117_scouting() -> None:
    state = _load(STATE)
    assert state["campaign116_terminal"]["terminal"] is True
    assert state["campaign116_terminal"]["predictive_direction_tested"] is False
    assert state["candidate49"]["only_active_prospective_candidate"] is True
    assert state["candidate49"]["signal_entry_count"] == 0
    assert state["candidate49"]["execution_entry_count"] == 0
    assert state["candidate49"]["historical_backfill_performed"] is False
    assert state["research_boundary"]["second_prospective_candidate_created"] is False
    assert "Campaign117" in state["next_action"]


def test_reports_record_terminal_metrics_and_no_investment_advice() -> None:
    paths = (
        ROOT / "docs/a_share_three_day_walkforward_campaign_116_terminal_report.md",
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
        ROOT / "docs/a_share_data_pipeline.md",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "Campaign116" in text
        assert "85.013381%" in text
        assert "71.417946%" in text
        assert "134" in text
        assert "Candidate49" in text
        assert "投资建议" in text


def test_terminal_timestamps_do_not_postdate_file_writes() -> None:
    for path in (AUDIT, LEDGER, RESULT, POLICY, STATE, ACTIVATION, FREEZE):
        recorded = datetime.fromisoformat(
            _load(path)["recorded_at"].replace("Z", "+00:00")
        )
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        assert recorded <= modified
