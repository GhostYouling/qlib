from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign064_no_return_audit as audit


AUDIT_PATH = (
    audit.REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_064/no_return/20260805T041624Z_campaign064_no_return_audit.json"
)
AUDIT_SHA256 = "55f3deef0cf8d58bf29a34e0af60cb290188dfe1f0e1d424e12e11ce18279c66"
LEDGER_PATH = (
    audit.REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_064/research_attempt_ledger_v11.json"
)
LEDGER_SHA256 = "b5e34071bc939c8b0703d5df5af871d2c01e47d8a783fa4326a4f7a96120e5ce"
SIGNAL_LEDGER = (
    audit.REPO_ROOT
    / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER = (
    audit.REPO_ROOT
    / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_terminal_audit_has_exact_ordered_rejection_semantics() -> None:
    assert _sha256(AUDIT_PATH) == AUDIT_SHA256
    record = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    factor = audit.FACTOR_NAME
    coverage = record["coverage_and_capacity"][factor]
    uniqueness = record["uniqueness"][factor]
    comparisons = uniqueness["comparisons"]
    expected = [item["name"] for item in audit.load_protocol()[
        "ordered_no_return_gates"
    ]["uniqueness_after_coverage_only"]["comparison_factors"]]
    observed = [item["comparison_factor"] for item in comparisons]
    failed = [item for item in comparisons if not item["gate_passed"]]
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["median_coverage"] >= 0.95
    assert coverage["p05_coverage"] >= 0.90
    assert coverage["eligible_names_p05"] >= 50
    assert coverage["potential_non_overlapping_three_session_cohorts"] >= 200
    assert len(coverage["observed_cohort_years"]) >= 5
    assert uniqueness["comparison_values_loaded_after_coverage_pass"] is True
    assert uniqueness["comparison_factor_count"] == 95
    assert uniqueness["comparison_order_matches_preregistration"] is True
    assert observed == expected
    assert all(item["gate_passed"] for item in comparisons[:-1])
    assert failed == [comparisons[-1]]
    assert comparisons[-1]["comparison_factor"] == audit.C63_FACTOR
    assert comparisons[-1]["pairwise_sessions"] == 0
    assert comparisons[-1]["median_daily_rank_correlation"] is None
    assert comparisons[-1]["gate_passed"] is False
    assert record["admissible_factor_count"] == 0
    assert record["status"] == (
        "completed_zero_admissible_factors_stop_before_historical_daily_prices_or_returns"
    )


def test_terminal_result_remains_return_and_prospective_closed() -> None:
    record = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    assert record["historical_daily_price_fields_read"] == []
    assert record["historical_forward_return_fields_read"] is False
    assert record["candidate49_historical_return_read"] is False
    assert record["candidate49_prospective_ledgers_changed"] is False
    assert record["provider_request_issued"] is False
    assert record["current_scoring_selection_sizing_or_orders_performed"] is False
    assert _sha256(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha256(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )


def test_append_only_attempt_accounting_is_terminal_and_complete() -> None:
    assert _sha256(LEDGER_PATH) == LEDGER_SHA256
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    assert ledger["attempt_count"] == 12
    assert ledger["complete_factor_attempt_count"] == 1
    assert ledger["return_reading_trial_count"] == 0
    entry = ledger["new_entries"][-1]
    assert entry["ordinal"] == 12
    assert entry["complete_factor_attempt"] is True
    assert entry["terminal"] is True
    assert entry["comparison_gate_pass_count"] == 94
    assert entry["comparison_gate_fail_count"] == 1
