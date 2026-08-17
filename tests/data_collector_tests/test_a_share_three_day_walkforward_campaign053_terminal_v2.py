"""Corrected terminal tests after preserving the Campaign053 report assertion failure."""

from __future__ import annotations

import importlib.util

import scripts.a_share_three_day_preregistration_binding_validator as bindings


_LEGACY_PATH = (
    __import__("pathlib").Path(__file__).with_name(
        "test_a_share_three_day_walkforward_campaign053_terminal.py"
    )
)
_SPEC = importlib.util.spec_from_file_location("campaign053_terminal_legacy", _LEGACY_PATH)
assert _SPEC is not None and _SPEC.loader is not None
legacy = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(legacy)
CURRENT_RECORD = (
    legacy.ROOT / "docs/a_share_three_day_walkforward_campaign_053_research_record_v2.json"
)
CURRENT_STATE = (
    legacy.ROOT / "docs/a_share_three_day_iteration_status_20260803_campaign053_verified_v2.json"
)
CURRENT_LEDGER = legacy.CROOT / "research_attempt_ledger_v2.json"


def test_campaign053_terminal_bindings_are_current() -> None:
    result = bindings.validate_record(CURRENT_RECORD, data_root=legacy.DATA_ROOT)
    assert result["all_bindings_passed"] is True


def test_campaign053_attempt_ledger_is_complete_and_append_only() -> None:
    ledger = legacy.load(CURRENT_LEDGER)
    assert ledger["append_only"] is True
    assert ledger["campaign053_attempt_count"] == 3
    assert ledger["campaign053_infrastructure_only_failure_count"] == 2
    assert ledger["campaign053_complete_factor_attempt_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 303
    assert ledger["campaign053_historical_return_trial_count"] == 0
    assert ledger["cumulative_return_reading_development_trial_count"] == 266
    assert ledger["post_terminal_delta_entries"][0]["sequence"] == 3


def test_campaign053_coverage_passed_but_uniqueness_failed_before_returns() -> None:
    legacy.test_campaign053_coverage_passed_but_uniqueness_failed_before_returns()


def test_campaign053_audit_verified_every_frozen_snapshot_and_boundary() -> None:
    legacy.test_campaign053_audit_verified_every_frozen_snapshot_and_boundary()


def test_campaign053_development_and_stress_stayed_closed() -> None:
    state = legacy.load(CURRENT_STATE)
    campaign = state["campaign053"]
    assert campaign["development"]["folds_opened"] is False
    assert campaign["development"]["trial_count"] == 0
    assert campaign["stress_2024_2025"]["opened"] is False
    assert campaign["stress_2024_2025"]["return_fields_read"] is False
    assert state["cumulative_state"]["current_historical_aggregation_candidate_count"] == 0


def test_campaign053_candidate49_ledgers_are_unchanged() -> None:
    legacy.test_campaign053_candidate49_ledgers_are_unchanged()


def test_campaign053_formula_is_terminal_without_rescue() -> None:
    legacy.test_campaign053_formula_is_terminal_without_rescue()


def test_unified_report_contains_campaign053_terminal_result() -> None:
    report = (
        legacy.ROOT / "data/experiments/short_horizon/three_day_research_report.md"
    ).read_text()
    assert "## 历史滚动 Campaign053 权威追加" in report
    assert "`+0.852858`" in report
    assert "累计历史研究尝试由 300 推进到 303" in report
