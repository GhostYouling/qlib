from __future__ import annotations

import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign102 as campaign

REPO_ROOT = Path(__file__).resolve().parents[2]
RECORD = REPO_ROOT / "docs/a_share_candidate49_20260807_daily_source_failure_record.json"
STATE = REPO_ROOT / "docs/a_share_three_day_iteration_status_20260807_campaign102_terminal_v3.json"


def test_failure_record_binds_exact_provider_artifact() -> None:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    failure = record["authoritative_failure"]
    path = Path(failure["path"])
    assert campaign.file_sha256(path) == failure["sha256"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["failure_stage"] == "stock_basic"
    assert payload["provider_calls_this_invocation"] == 4
    assert payload["active_root_mutated"] is False
    assert payload["credential_value_persisted"] is False
    assert payload["forward_return_fields_read"] is False


def test_same_day_retry_and_continuation_are_closed() -> None:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    assert record["run"]["exit_code"] == 1
    assert record["run"]["provider_continuation_allowed"] is False
    policy = record["same_day_policy"]
    assert policy["provider_retry_allowed"] is False
    assert policy["failed_response_may_be_re_requested_for_more_detail"] is False
    assert policy["failure_exit_code_may_be_bypassed"] is False


def test_candidate49_ledgers_remain_empty_and_unchanged() -> None:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    candidate = record["candidate49"]
    signal = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    execution = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    assert campaign.file_sha256(signal) == candidate["signal_ledger_sha256"]
    assert campaign.file_sha256(execution) == candidate["execution_ledger_sha256"]
    assert json.loads(signal.read_text(encoding="utf-8"))["entries"] == []
    assert json.loads(execution.read_text(encoding="utf-8"))["entries"] == []


def test_current_state_binds_failure_and_keeps_offline_research_open() -> None:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    binding = state["candidate49_20260807_source_failure"]
    assert campaign.file_sha256(RECORD) == binding["sha256"]
    assert binding["same_day_retry_allowed"] is False
    assert state["research_mode"]["candidate49_failure_does_not_block_offline_campaign103"] is True
    assert state["current_scoring_selection_sizing_or_orders_performed"] is False
