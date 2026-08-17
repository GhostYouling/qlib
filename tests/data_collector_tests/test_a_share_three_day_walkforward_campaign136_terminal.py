from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings


ROOT = Path(__file__).resolve().parents[2]
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_136_terminal_result_v7_20260814.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v169_20260814.json"
)
STATUS = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260814_campaign136_terminal_v6.json"
)
WALKFORWARD = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_136/walkforward"
)
BASE_ATTEMPTS = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_136/research_attempt_ledger.json"
)
DEVELOPMENT_DELTA = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_136/research_attempt_ledger_terminal_delta.json"
)
TERMINAL_DELTA = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_136/research_attempt_ledger_terminal_delta_v7.json"
)
INTERMEDIATE_DELTAS = tuple(
    ROOT
    / f"data/experiments/short_horizon/historical_walkforward/campaign_136/research_attempt_ledger_terminal_delta_v{version}.json"
    for version in range(2, 7)
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _attempt_hash(attempt_id: str, previous: str, phase: str, status: str) -> str:
    payload = f"campaign136|{attempt_id}|{previous}|{phase}|{status}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_terminal_bindings_and_zero_survivor_semantics() -> None:
    assert bindings.validate_record(TERMINAL)["all_bindings_passed"] is True
    terminal = _load(TERMINAL)
    survivors = _load(WALKFORWARD / "development_survivors.json")
    stress = _load(WALKFORWARD / "exposed_stress_consumption_record.json")
    assert terminal["scientific_result"]["development_survivor_count"] == 0
    assert survivors["selected_survivor_count"] == 0
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False


def test_exact_one_frozen_trial_and_rejection_metrics_are_preserved() -> None:
    ledger = _load(WALKFORWARD / "trial_ledger.json")
    terminal = _load(TERMINAL)["scientific_result"]
    assert len(ledger["entries"]) == 1
    assert ledger["entries"][0]["trial_id"] == terminal["trial_id"]
    assert terminal["positive_mean_rank_ic_fold_count"] == 1
    assert terminal["positive_normalized_return_fold_count"] == 0
    assert terminal["positive_pilot_10bp_return_fold_count"] == 0
    assert terminal["median_validation_mean_rank_ic"] == (-0.0016011400195721482)
    assert terminal["median_validation_pilot_10bp_return"] == (-0.030260889042400763)
    assert terminal["development_aggregate_20bp_return"] == (-0.16763486989091458)


def test_append_only_attempt_deltas_chain_without_rewriting_base() -> None:
    base = _load(BASE_ATTEMPTS)
    delta_paths = (DEVELOPMENT_DELTA, *INTERMEDIATE_DELTAS, TERMINAL_DELTA)
    deltas = [_load(path) for path in delta_paths]
    assert _sha(BASE_ATTEMPTS) == deltas[0]["authoritative_predecessor"]["sha256"]
    for predecessor_path, delta in zip(delta_paths, deltas[1:]):
        assert _sha(predecessor_path) == delta["authoritative_predecessor"]["sha256"]
    for delta in deltas:
        entry = delta["entries"][0]
        assert entry["entry_sha256"] == _attempt_hash(
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    assert base["entry_count"] == 11
    terminal = deltas[-1]
    assert terminal["effective_entry_count"] == 18
    assert terminal["effective_infrastructure_failure_attempt_count"] == 11
    assert terminal["effective_return_reading_development_trial_count"] == 1
    assert terminal["cumulative_historical_research_attempt_count"] == 1138
    assert terminal["cumulative_return_reading_development_trial_count"] == 313


def test_v169_preserves_campaign136_numeric_series_once_after_terminal() -> None:
    policy = _load(POLICY)
    assert bindings.validate_record(POLICY)["all_bindings_passed"] is True
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"] == 152
    )
    assert policy["complete_historical_feature_library"]["order_sha256"] == (
        "60c465a3e2043efae6b92b8c5f3e007cd397a1cd0ec3094b4fa005665bbe5736"
    )
    numeric = policy["numerical_comparator_eligibility"]
    assert numeric["eligible_numeric_comparator_count"] == 141
    assert numeric["eligible_numeric_comparator_order_sha256"] == (
        "ec1aebcb939ad516c58037a36a4aaadd4ad8b2abbd3c884705895c58da85a2ee"
    )
    assert numeric[
        "campaign136_numeric_series_appended_once_after_terminal_classification"
    ]


def test_candidate49_and_current_action_boundaries_remain_closed() -> None:
    terminal = _load(TERMINAL)
    signal = (
        ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    )
    execution = (
        ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    )
    assert _sha(signal) == terminal["candidate49"]["signal_ledger_sha256"]
    assert _sha(execution) == terminal["candidate49"]["execution_ledger_sha256"]
    assert terminal["candidate49"]["signal_entry_count"] == 0
    assert terminal["candidate49"]["execution_entry_count"] == 0
    boundary = terminal["research_boundary"]
    assert boundary["stress_2024_2025_opened"] is False
    assert boundary["candidate49_historical_backfill_performed"] is False
    assert boundary["second_prospective_candidate_created"] is False
    assert (
        boundary["current_scoring_selection_sizing_positions_or_orders_performed"]
        is False
    )


def test_status_and_reports_record_terminal_result_and_active_goal() -> None:
    validation = bindings.validate_record(STATUS)
    assert validation["passed_binding_count"] == 6
    assert {item["json_pointer"] for item in validation["failed_bindings"]} == {
        "/reports/current_research_report",
        "/reports/three_day_research_report",
    }
    status = _load(STATUS)
    assert status["goal"]["status"] == "active"
    assert status["campaign136"]["terminal"] is True
    assert status["campaign136"]["stress_2024_2025_opened"] is False
    assert (
        status["local_daily_boundary"][
            "candidate49_plan_run_or_source_request_performed"
        ]
        is False
    )
    for relative in (
        "docs/a_share_three_day_walkforward_campaign_136_terminal_report.md",
        "data/experiments/short_horizon/current_research_report.md",
        "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "Campaign136" in text
        assert "2024–2025" in text
        assert "152/141" in text
