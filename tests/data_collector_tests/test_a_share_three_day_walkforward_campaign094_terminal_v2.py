from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign094_features_v4 as definitions

ROOT = definitions.REPO_ROOT
TERMINAL_STATE = (
    ROOT / "docs/a_share_three_day_iteration_status_20260807_campaign094_terminal.json"
)
TERMINAL_STATE_SHA256 = (
    "643d8228fc0c62c713a9817b6d59ac229002296e64a63ec9cae738550ed4295e"
)
RESEARCH_V2 = (
    ROOT / "docs/a_share_three_day_walkforward_campaign_094_research_record_v2.json"
)
RESEARCH_V2_SHA256 = "eca640cea1b85b6482c7ffdcbcb5d93d01ad7ffd7cd18ce88f289f62ff62b6c7"
FREEZE_V2 = ROOT / (
    "docs/a_share_three_day_walkforward_campaign_094_terminal_completion_freeze_v2_20260807.json"
)
FREEZE_V2_SHA256 = "1b82c9cd22c79c4fa4d9b135e5238a478ac279894778339be5b1becc679bfff0"
POLICY_V38 = ROOT / (
    "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_"
    "policy_v38_20260807.json"
)
POLICY_V38_SHA256 = "38994cc61f350f40a9a85d75a30a6e36831d968416799284413247e8d2cd4b42"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_effective_v2_terminal_chain_and_timestamps_are_exact() -> None:
    for path, expected in (
        (TERMINAL_STATE, TERMINAL_STATE_SHA256),
        (RESEARCH_V2, RESEARCH_V2_SHA256),
        (FREEZE_V2, FREEZE_V2_SHA256),
        (POLICY_V38, POLICY_V38_SHA256),
    ):
        assert _sha256(path) == expected
        assert bindings.validate_record(path)["all_bindings_passed"] is True
        record = _load(path)
        timestamp = record.get("recorded_at")
        if timestamp is not None:
            assert datetime.fromisoformat(timestamp.replace("Z", "+00:00")) <= (
                datetime.now(timezone.utc)
            )


def test_final_attempt_and_report_bindings_are_current() -> None:
    record = _load(RESEARCH_V2)
    final_ledger = record["final_attempt_ledger"]
    path = ROOT / final_ledger["path"]
    assert _sha256(path) == final_ledger["sha256"]
    ledger = _load(path)
    assert ledger["campaign094_attempt_count"] == 6
    assert ledger["campaign094_ledger_entry_count"] == 9
    assert ledger["campaign094_infrastructure_or_implementation_failure_count"] == 5
    assert ledger["cumulative_historical_research_attempt_count"] == 656
    assert ledger["cumulative_return_reading_development_trial_count"] == 291
    for binding in record["reporting_bindings"].values():
        report = ROOT / binding["path"]
        assert _sha256(report) == binding["sha256"]
        text = report.read_text(encoding="utf-8")
        assert "Campaign094" in text
        assert "656" in text


def test_scientific_result_and_v38_orders_remain_exact() -> None:
    state = _load(TERMINAL_STATE)
    result = state["campaign094_result"]
    assert result["numeric_comparisons_passed"] == 123
    assert result["development_trial_count"] == 1
    assert result["development_survivor_count"] == 0
    assert result["stress_2024_2025_opened"] is False
    policy = _load(POLICY_V38)
    factor = {"name": definitions.FACTOR_NAME, "score_direction": "higher"}
    complete = definitions.reconstruct_complete_definitions() + [factor]
    numeric = definitions.reconstruct_comparisons() + [factor]
    assert len(complete) == 126
    assert len(numeric) == 124
    assert definitions._comparison_order_digest(complete) == (
        policy["complete_historical_feature_library"]["order_sha256"]
    )
    assert definitions._comparison_order_digest(numeric) == (
        policy["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_order_sha256"
        ]
    )


def test_candidate49_empty_ledgers_and_research_boundary_are_unchanged() -> None:
    state = _load(TERMINAL_STATE)
    candidate49 = state["candidate49"]
    signal = (
        ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    )
    execution = (
        ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    )
    assert _sha256(signal) == candidate49["signal_ledger_sha256"]
    assert _sha256(execution) == candidate49["execution_ledger_sha256"]
    assert candidate49["signal_ledger_entry_count"] == 0
    assert candidate49["execution_ledger_entry_count"] == 0
    assert candidate49["provider_request_issued_this_iteration"] is False
    assert candidate49["same_day_plan_or_run_executed_this_iteration"] is False
    record = _load(RESEARCH_V2)
    assert (
        record["research_boundary"]["additional_development_or_stress_return_read"]
        is False
    )
    assert (
        record["research_boundary"][
            "current_scoring_selection_sizing_or_orders_performed"
        ]
        is False
    )
