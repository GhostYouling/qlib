from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings


ROOT = Path(__file__).resolve().parents[2]
FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_148_campaign145_mutable_report_lifecycle_validation_failure_20260814.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_148/research_attempt_ledger_v2.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_148_terminal_result_v2_20260814.json"
)
CURRENT_REPORT = ROOT / "data/experiments/short_horizon/current_research_report.md"
THREE_DAY_REPORT = ROOT / "data/experiments/short_horizon/three_day_research_report.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _entry_hash(entry: dict) -> str:
    payload = "|".join(
        (
            "campaign148",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_campaign148_records_historical_mutable_report_lifecycle_failure() -> None:
    failure = _load(FAILURE)
    assert failure["process_exit_code"] == 1
    assert failure["test_result"] == {
        "passed": 99,
        "failed": 1,
        "skipped": 1,
        "failed_node": (
            "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign145_terminal.py::"
            "test_campaign145_terminal_bindings_reports_and_candidate49_boundary"
        ),
    }
    assert failure["diagnosis"]["failed_bindings"] == 2
    handling = failure["handling"]
    assert handling["failed_exit_code_bypassed_or_masked"] is False
    assert handling["campaign145_record_or_test_rewritten"] is False
    assert handling["binding_validator_weakened_or_modified"] is False
    assert handling["scientific_result_changed"] is False
    assert handling["candidate_comparator_price_or_return_value_read"] is False


def test_campaign148_effective_delta_ledger_and_terminal_accounting() -> None:
    for path in (FAILURE, LEDGER, TERMINAL):
        assert bindings.validate_record(path)["all_bindings_passed"] is True

    ledger = _load(LEDGER)
    assert ledger["effective_entry_count"] == 7
    assert ledger["effective_attempt_count"] == 7
    assert ledger["effective_prevalue_concept_attempt_count"] == 6
    assert ledger["effective_infrastructure_failure_attempt_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 1287
    assert ledger["cumulative_return_reading_development_trial_count"] == 314
    assert len(ledger["entries"]) == 1
    entry = ledger["entries"][0]
    assert entry["entry_sha256"] == _entry_hash(entry)
    assert entry["entry_sha256"] == ledger["chain_tip_sha256"]

    terminal = _load(TERMINAL)
    accounting = terminal["effective_accounting"]
    assert accounting["campaign148_attempt_count"] == 7
    assert accounting["campaign148_infrastructure_failure_count"] == 1
    assert accounting["campaign148_return_reading_development_trial_count"] == 0
    assert accounting["cumulative_historical_research_attempt_count"] == 1287
    scientific = terminal["scientific_result_unchanged"]
    assert scientific["selected_candidate_count"] == 0
    assert (
        scientific[
            "source_candidate_comparator_daily_price_or_forward_return_values_read"
        ]
        is False
    )
    assert scientific["complete_factor_definition_count"] == 155
    assert scientific["eligible_numeric_comparator_count"] == 142


def test_campaign148_accounting_correction_is_appended_once_to_reports() -> None:
    heading = "### Campaign148 发布后兼容性会计追加"
    assert CURRENT_REPORT.read_text(encoding="utf-8").count(heading) == 1
    assert THREE_DAY_REPORT.read_text(encoding="utf-8").count(heading) == 1
