"""Focused tests for the frozen Campaign032 disclosure-timeliness factor."""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

import numpy as np
import pytest

import scripts.a_share_three_day_preregistration_binding_validator as bindings


MODULE = importlib.import_module(
    "scripts.a_share_three_day_walkforward_campaign032_features"
)
REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_032"
    / "no_return/20260730T154237Z_campaign032_no_return_audit.json"
)
RESEARCH_RECORD_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_032_research_record.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_factor_uses_exact_negative_integer_calendar_day_delay():
    values, eligible, quality = MODULE.compute_factor_values(
        np.array([-30.0, 0.0, np.nan, -91.0])
    )

    assert values[MODULE.FACTOR_NAME].tolist()[:2] == [-30.0, 0.0]
    assert np.isnan(values[MODULE.FACTOR_NAME][2])
    assert values[MODULE.FACTOR_NAME][3] == -91.0
    assert eligible[MODULE.FACTOR_NAME].tolist() == [True, True, False, True]
    assert quality[f"{MODULE.FACTOR_NAME}__eligible_rows"] == 3


@pytest.mark.parametrize("invalid", [1.0, -1.5, np.inf, -np.inf])
def test_positive_noninteger_or_nonfinite_scores_are_missing(invalid):
    values, eligible, _ = MODULE.compute_factor_values(np.array([invalid]))

    assert not eligible[MODULE.FACTOR_NAME][0]
    assert np.isnan(values[MODULE.FACTOR_NAME][0])


def test_protocol_v2_is_complete_unique_and_binding_valid():
    spec = MODULE.load_protocol()
    comparisons = spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]

    assert len(comparisons) == 53
    assert len({item["name"] for item in comparisons}) == 53
    assert comparisons[-1]["name"] == (
        "intraday_market_dispersion_decoupling_238m"
    )
    assert spec["candidates"][0]["name"] == MODULE.FACTOR_NAME


def test_reporting_range_covers_every_finite_nonpositive_float():
    lower, upper = MODULE.FACTOR_RANGES[MODULE.FACTOR_NAME]

    assert lower == -np.finfo(np.float64).max
    assert upper == 0.0


def test_no_return_audit_is_bound_and_terminal_on_uniqueness():
    audit = json.loads(AUDIT_PATH.read_text())
    uniqueness = audit["uniqueness"][MODULE.FACTOR_NAME]
    failed = [
        item for item in uniqueness["comparisons"] if not item["gate_passed"]
    ]

    assert _sha256(AUDIT_PATH) == MODULE.NO_RETURN_AUDIT_SHA256
    assert audit["status"] == (
        "completed_zero_admissible_factors_stop_before_historical_returns"
    )
    assert audit["admissible_factor_count"] == 0
    assert uniqueness["comparison_factor_count"] == 53
    assert uniqueness["comparison_order_matches_preregistration"] is True
    assert uniqueness["all_required_comparisons_passed"] is False
    assert len(failed) == 1
    assert failed[0]["comparison_factor"] == (
        "quarterly_announcement_freshness_60s"
    )
    assert failed[0]["median_daily_rank_correlation"] == pytest.approx(
        -0.9793254451074888
    )
    assert failed[0]["absolute_median_daily_rank_correlation"] > 0.8


def test_terminal_record_preserves_no_return_and_candidate49_boundaries():
    record = json.loads(RESEARCH_RECORD_PATH.read_text())
    validation = bindings.validate_record(
        RESEARCH_RECORD_PATH,
        data_root=MODULE.DEFAULT_DATA_ROOT,
    )

    assert validation["all_bindings_passed"] is True
    assert record["terminal_decision"]["campaign032_terminal"] is True
    assert record["trial_accounting"]["development_preregistration_created"] is False
    assert record["trial_accounting"]["development_trial_count"] == 0
    assert (
        record["trial_accounting"][
            "cumulative_historical_development_trial_count_after_campaign"
        ]
        == 253
    )
    assert record["trial_accounting"]["development_return_fields_read"] is False
    assert record["trial_accounting"]["stress_2024_2025_opened"] is False
    assert (
        record["candidate49_state_after_campaign"]["signal_ledger"]["entry_count"]
        == 0
    )
    assert (
        record["candidate49_state_after_campaign"]["execution_ledger"][
            "entry_count"
        ]
        == 0
    )


def test_unified_report_contains_campaign032_terminal_result():
    report = (
        REPO_ROOT
        / "data/experiments/short_horizon/three_day_research_report.md"
    ).read_text()

    assert "## 历史滚动 Campaign032 权威追加" in report
    assert "绝对值 0.979325 超过冻结上限 0.80" in report
    assert "累计历史开发试验仍为 253" in report
