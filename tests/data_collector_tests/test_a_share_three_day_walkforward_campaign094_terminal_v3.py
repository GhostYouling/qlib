from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign094_features_v4 as definitions

ROOT = definitions.REPO_ROOT
RESEARCH = (
    ROOT / "docs/a_share_three_day_walkforward_campaign_094_research_record_v3.json"
)
RESEARCH_SHA256 = "629176b4947395977ae8d217716fed8976b0718e262ce51d9d5d392b80cd4d03"
FREEZE = ROOT / (
    "docs/a_share_three_day_walkforward_campaign_094_terminal_completion_freeze_v3_20260807.json"
)
FREEZE_SHA256 = "1f8d0c0d591ca83c081585a9ffb378b0bd20dcbd33ab6de6b17d847f8efeed78"
POLICY = ROOT / (
    "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_"
    "policy_v38_20260807.json"
)
POLICY_SHA256 = "38994cc61f350f40a9a85d75a30a6e36831d968416799284413247e8d2cd4b42"
TERMINAL_STATE = (
    ROOT / "docs/a_share_three_day_iteration_status_20260807_campaign094_terminal.json"
)
TERMINAL_STATE_SHA256 = (
    "643d8228fc0c62c713a9817b6d59ac229002296e64a63ec9cae738550ed4295e"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_final_effective_chain_and_timestamps_are_exact() -> None:
    for path, expected in (
        (RESEARCH, RESEARCH_SHA256),
        (FREEZE, FREEZE_SHA256),
        (POLICY, POLICY_SHA256),
        (TERMINAL_STATE, TERMINAL_STATE_SHA256),
    ):
        assert _sha256(path) == expected
        assert bindings.validate_record(path)["all_bindings_passed"] is True
        timestamp = _load(path).get("recorded_at")
        if timestamp is not None:
            assert datetime.fromisoformat(timestamp.replace("Z", "+00:00")) <= (
                datetime.now(timezone.utc)
            )


def test_final_accounting_and_reports_are_exact() -> None:
    record = _load(RESEARCH)
    ledger_binding = record["effective_final_attempt_ledger"]
    ledger_path = ROOT / ledger_binding["path"]
    assert _sha256(ledger_path) == ledger_binding["sha256"]
    ledger = _load(ledger_path)
    assert ledger["campaign094_attempt_count"] == 7
    assert ledger["campaign094_ledger_entry_count"] == 10
    assert ledger["campaign094_infrastructure_or_implementation_failure_count"] == 6
    assert ledger["campaign094_return_reading_development_trial_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 657
    assert ledger["cumulative_return_reading_development_trial_count"] == 291
    for binding in record["reporting_bindings"].values():
        report = ROOT / binding["path"]
        assert _sha256(report) == binding["sha256"]
        text = report.read_text(encoding="utf-8")
        assert "Campaign094" in text
        assert "657" in text


def test_scientific_result_and_v38_orders_are_unchanged() -> None:
    record = _load(RESEARCH)
    result = record["scientific_result"]
    assert result["coverage_and_123_numeric_uniqueness_gates_passed"] is True
    assert result["development_trial_count"] == 1
    assert result["development_survivor_count"] == 0
    assert result["stress_2024_2025_opened"] is False
    policy = _load(POLICY)
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


def test_candidate49_and_current_action_boundaries_remain_closed() -> None:
    record = _load(RESEARCH)
    candidate49 = record["candidate49"]
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
    assert candidate49["provider_request_issued"] is False
    assert candidate49["historical_backfill_performed"] is False
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
