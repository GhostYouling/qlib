from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign128_features as c128


ROOT = Path(__file__).resolve().parents[2]
CAPACITY = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_139/capacity/campaign139_capacity_audit.json"
)
LEDGER_V2 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_139/research_attempt_ledger_v2.json"
)
LEDGER_V3 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_139/research_attempt_ledger_v3.json"
)
LEDGER_V4 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_139/research_attempt_ledger_v4.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_139_terminal_result_20260814.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v176_20260814.json"
)
STATUS = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260814_campaign139_capacity_terminal_v2.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _entry_hash(entry: dict) -> str:
    payload = "|".join(
        (
            "campaign139",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _definition_digest(items: list[list[str]]) -> str:
    payload = json.dumps(
        items,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_campaign139_capacity_failure_is_terminal_before_comparators_or_returns() -> (
    None
):
    capacity = _load(CAPACITY)
    assert capacity["status"] == (
        "capacity_failed_terminal_before_all_comparator_values"
    )
    metrics = capacity["capacity"]
    assert metrics["capacity_gate_passed_before_comparator_values"] is False
    assert metrics["potential_complete_cohorts"] == 123
    assert (
        metrics["gate"]["minimum_non_overlapping_three_signal_session_cohorts"] == 200
    )
    assert metrics["observed_cohort_years"] == [2019, 2020, 2021, 2022, 2023]
    assert capacity["numeric_comparator_count_read"] == 0
    assert capacity["comparator_values_read"] is False
    assert capacity["historical_daily_price_or_forward_return_values_read"] is False
    assert capacity["stress_2024_2025_opened"] is False


def test_campaign139_append_only_continuation_chain_and_accounting() -> None:
    ledger = _load(LEDGER_V4)
    assert _sha(LEDGER_V3) == ledger["authoritative_predecessor"]["sha256"]
    previous = ledger["authoritative_predecessor"]["chain_tip_sha256"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        previous = entry["entry_sha256"]
    assert ledger["chain_tip_sha256"] == previous
    assert ledger["effective_entry_count"] == 15
    assert ledger["effective_attempt_count"] == 13
    assert ledger["effective_infrastructure_failure_attempt_count"] == 7
    assert ledger["effective_complete_factor_attempt_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 1168
    assert ledger["cumulative_return_reading_development_trial_count"] == 313


def test_campaign139_definition_appends_once_but_numeric_order_stays_closed() -> None:
    prior = [
        [item["name"], item["score_direction"]]
        for item in c128.reconstruct_complete_definitions()
    ]
    prior.append(["daily_realized_price_basis_adjustment_magnitude_1d", "higher"])
    assert len(prior) == 152
    assert _definition_digest(prior) == (
        "60c465a3e2043efae6b92b8c5f3e007cd397a1cd0ec3094b4fa005665bbe5736"
    )
    prior.append(["quarterly_realized_profit_growth_forecast_surprise_rank", "higher"])
    assert len(prior) == 153
    assert _definition_digest(prior) == (
        "bf66faef96d7058c7028da52757c65d8e0bf7978cf72d3967cd236e4da30b875"
    )
    policy = _load(POLICY)
    assert bindings.validate_record(POLICY)["all_bindings_passed"] is True
    complete = policy["complete_historical_feature_library"]
    numeric = policy["numerical_comparator_eligibility"]
    assert complete["factor_definition_count"] == 153
    assert complete["order_sha256"] == _definition_digest(prior)
    assert numeric["eligible_numeric_comparator_count"] == 141
    assert numeric["eligible_numeric_comparator_order_sha256"] == (
        "ec1aebcb939ad516c58037a36a4aaadd4ad8b2abbd3c884705895c58da85a2ee"
    )
    assert numeric["campaign139_numeric_series_appended"] is False


def test_campaign139_terminal_status_goal_and_candidate49_isolation() -> None:
    assert bindings.validate_record(TERMINAL)["all_bindings_passed"] is True
    assert bindings.validate_record(STATUS)["all_bindings_passed"] is True
    terminal = _load(TERMINAL)
    status = _load(STATUS)
    signal = (
        ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    )
    execution = (
        ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    )
    assert _sha(signal) == terminal["candidate49"]["signal_ledger_sha256"]
    assert _sha(execution) == terminal["candidate49"]["execution_ledger_sha256"]
    assert status["goal"]["status"] == "active"
    assert status["campaign139"]["terminal"] is True
    assert status["campaign139"]["numeric_comparator_count_read"] == 0
    assert status["candidate49"]["signal_entries"] == 0
    assert status["candidate49"]["execution_entries"] == 0
    assert status["local_daily_boundary"]["after_16_30_asia_singapore"] is False
    assert (
        status["local_daily_boundary"][
            "candidate49_plan_run_or_source_request_performed"
        ]
        is False
    )


def test_campaign139_reports_record_terminal_failure_without_trading_output() -> None:
    for relative in (
        "docs/a_share_three_day_walkforward_campaign_139_terminal_report_v2.md",
        "data/experiments/short_horizon/current_research_report.md",
        "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "Campaign139" in text
        assert "123" in text
        assert "200" in text
        assert "153/141" in text
        assert "1168" in text or "1,168" in text
