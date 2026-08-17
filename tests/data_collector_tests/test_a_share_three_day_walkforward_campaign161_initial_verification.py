from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FAILURES_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_161_initial_verification_failures_20260815.json"
)
LEDGER_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_161/research_attempt_ledger_v1.json"
)
POLICY_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v224_20260815.json"
)
STATE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_iteration_status_20260815_campaign161_initial_verification.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve(path: str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else REPO_ROOT / value


def test_campaign161_failure_record_is_complete_and_recovered() -> None:
    record = _load(FAILURES_PATH)
    assert record["status"] == (
        "two_read_only_verification_command_failures_recorded_and_recovered_without_research_value_access"
    )
    failures = record["failures"]
    assert [item["attempt_id"] for item in failures] == [
        "campaign161_infrastructure_001",
        "campaign161_infrastructure_002",
    ]
    assert [item["exit_code"] for item in failures] == [127, 4]
    assert all(not item["partial_output_or_target_write"] for item in failures)
    assert record["safe_recovery"]["recovery_exit_code"] == 0
    assert record["safe_recovery"]["json_parse_passed"] == 10
    assert record["safe_recovery"]["receipt_authoritative_input_bindings_passed"] == 13
    assert record["safe_recovery"]["binding_validator_bindings_passed"] == 13
    assert not record["safe_recovery"]["failed_exit_codes_bypassed_or_masked"]
    assert not any(record["research_boundary"].values())


def test_campaign161_ledger_hash_chain_and_accounting() -> None:
    ledger = _load(LEDGER_PATH)
    previous = ledger["authoritative_predecessor"]["chain_tip_sha256"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign161",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        )
        assert entry["entry_sha256"] == hashlib.sha256(payload.encode()).hexdigest()
        previous = entry["entry_sha256"]
    assert ledger["chain_tip_sha256"] == previous
    assert ledger["effective_entry_count"] == 2
    assert ledger["effective_prevalue_scientific_attempt_count"] == 0
    assert ledger["effective_infrastructure_failure_attempt_count"] == 2
    assert ledger["cumulative_historical_research_attempt_count"] == 1398
    assert ledger["cumulative_return_reading_development_trial_count"] == 314
    assert not ledger["scientific_state"]["campaign161_scientific_attempt_started"]


def test_campaign161_policy_state_and_all_immutable_bindings() -> None:
    for record_path in [FAILURES_PATH, LEDGER_PATH, POLICY_PATH, STATE_PATH]:
        record = _load(record_path)
        for binding in record.get("authoritative_inputs", {}).values():
            bound_path = _resolve(binding["path"])
            assert bound_path.is_file()
            assert _sha256(bound_path) == binding["sha256"]

    policy = _load(POLICY_PATH)
    state = _load(STATE_PATH)
    assert policy["version"] == 224
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"] == 157
    )
    assert (
        policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"]
        == 142
    )
    assert policy["campaign161_active_classification"]["terminal"] is False
    assert state["goal"]["status"] == "active"
    assert state["goal"]["campaign161_started"] is True
    assert state["goal"]["campaign161_scientific_attempt_started"] is False
    assert state["candidate49"]["sole_prospective_candidate"] is True
    assert state["candidate49"]["signal_ledger"]["entries"] == 0
    assert state["candidate49"]["execution_ledger"]["entries"] == 0
    assert state["candidate49_daily_20260815"]["accepted_local_trading_day"] is False
    assert not any(state["research_boundary"].values())


def test_campaign161_reports_and_candidate49_hashes() -> None:
    state = _load(STATE_PATH)
    heading = "## Campaign161 启动与 Campaign160 验证回执复核"
    for report in state["reports"].values():
        report_path = _resolve(report["path"])
        assert report_path.read_text(encoding="utf-8").count(heading) == 1
        assert _sha256(report_path) == report["sha256_at_publication"]

    for ledger_name in ["signal_ledger", "execution_ledger"]:
        binding = state["candidate49"][ledger_name]
        assert _sha256(_resolve(binding["path"])) == binding["sha256"]
        assert binding["entries"] == 0
