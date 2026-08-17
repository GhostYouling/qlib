from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.a_share_three_day_preregistration_binding_validator import (
    validate_record,
)


ROOT = Path(__file__).resolve().parents[2]
FAILURES = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_105_prevalue_infrastructure_failures_v2_20260808.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_105/research_attempt_ledger_v2.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260808_campaign105_preregistered_verified.json"
)
SIGNAL_LEDGER = (
    ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER = (
    ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_current_campaign105_prevalue_node_hashes_are_exact() -> None:
    assert (
        _sha256(FAILURES)
        == "4411e359a2d39b8125c7590820c464f4e80901b1fd23c3b3c1c1c53fd4598a54"
    )
    assert (
        _sha256(LEDGER)
        == "6b3bcba854cbd79a2aa11eda038c98fcc37d77f221bc55447ec0cbdb5ba8ebb1"
    )
    assert (
        _sha256(STATE)
        == "2c70d2c04e98ba0ffca6da30209b21e50fc6ed3801be478cc87480cfa218ba99"
    )


def test_current_append_only_accounting_and_chain_are_exact() -> None:
    ledger = _load(LEDGER)
    assert ledger["attempt_count"] == len(ledger["entries"]) == 4
    assert ledger["infrastructure_failure_count"] == 3
    assert ledger["prevalue_scientific_attempt_count"] == 1
    assert ledger["complete_factor_attempt_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 779
    assert ledger["cumulative_return_reading_development_trial_count"] == 299
    previous = ledger["chain_genesis"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = (
            "campaign105|"
            + entry["attempt_id"]
            + "|"
            + previous
            + "|"
            + entry["phase"]
            + "|"
            + entry["status"]
        ).encode()
        assert hashlib.sha256(payload).hexdigest() == entry["entry_sha256"]
        previous = entry["entry_sha256"]
    assert previous == ledger["chain_tip_sha256"]


def test_verified_state_bindings_and_research_boundaries_pass() -> None:
    result = validate_record(STATE, data_root=DATA_ROOT)
    assert result["binding_count"] == 12
    assert result["failed_binding_count"] == 0
    assert result["all_bindings_passed"] is True

    state = _load(STATE)
    candidate = state["campaign105_prevalue"]["candidate"]
    assert candidate["formula_frozen"] is True
    assert candidate["implementation_fingerprint_frozen"] is False
    assert candidate["feature_snapshot_created"] is False
    assert candidate["candidate_values_computed_or_read"] is False
    assert candidate["comparison_values_read"] is False
    assert candidate["historical_daily_price_or_forward_return_values_read"] is False
    assert candidate["development_trial_run"] is False
    assert candidate["stress_2024_2025_opened"] is False
    assert (
        state["provider_request_accounting"][
            "campaign105_historical_research_provider_calls"
        ]
        == 0
    )
    assert (
        state["provider_request_accounting"]["candidate49_provider_calls_on_2026_08_08"]
        == 0
    )
    assert state["current_scoring_selection_sizing_or_orders_performed"] is False
    assert state["investment_advice"] is False


def test_candidate49_and_credential_presence_semantics_remain_unchanged() -> None:
    state = _load(STATE)
    candidate49 = state["candidate49"]
    assert _sha256(SIGNAL_LEDGER) == candidate49["signal_ledger_sha256"]
    assert _sha256(EXECUTION_LEDGER) == candidate49["execution_ledger_sha256"]
    assert candidate49["signal_entry_count"] == 0
    assert candidate49["execution_entry_count"] == 0
    assert candidate49["historical_backfill_performed"] is False
    assert candidate49["second_prospective_candidate_created"] is False
    credential = state["provider_credential"]
    assert credential["recognized_nonempty_token_key_count"] == 1
    assert credential["workflow_loader_observed_nonempty_token"] is True
    assert credential["secret_printed_hashed_logged_or_persisted"] is False


def test_current_records_have_nonfuture_logical_timestamps() -> None:
    for path in (FAILURES, LEDGER, STATE):
        recorded = datetime.fromisoformat(
            _load(path)["recorded_at"].replace("Z", "+00:00")
        )
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        assert recorded <= modified
