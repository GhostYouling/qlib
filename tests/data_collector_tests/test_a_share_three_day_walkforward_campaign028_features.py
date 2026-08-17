import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_preregistration_binding_validator as BINDINGS
import scripts.a_share_three_day_walkforward_campaign028_features as FEATURES
import scripts.a_share_three_day_walkforward_campaign028 as WALKFORWARD


REPO_ROOT = Path(__file__).resolve().parents[2]


def _close_path(
    morning_returns: np.ndarray,
    afternoon_returns: np.ndarray,
) -> np.ndarray:
    morning = np.exp(np.r_[0.0, np.cumsum(morning_returns)])
    afternoon = np.exp(np.r_[0.0, np.cumsum(afternoon_returns)])
    return np.r_[morning, afternoon]


def _expected_persistence(
    morning_returns: np.ndarray,
    afternoon_returns: np.ndarray,
) -> float:
    morning = np.abs(morning_returns)
    afternoon = np.abs(afternoon_returns)
    lag = np.r_[morning[:-1], afternoon[:-1]]
    lead = np.r_[morning[1:], afternoon[1:]]
    return float(np.corrcoef(lag, lead)[0, 1])


def test_absolute_return_persistence_exact_positive_negative_and_degenerate() -> None:
    increasing = np.linspace(0.0001, 0.01, 119)
    alternating = np.resize(np.array([0.001, 0.01]), 119)
    closes = np.vstack(
        (
            _close_path(increasing, increasing),
            _close_path(alternating, alternating),
            np.ones(FEATURES.SELECTED_BAR_COUNT),
        )
    )
    values, eligible, quality = FEATURES.compute_factor_values(closes=closes)
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True, False]
    assert values[FEATURES.FACTOR_NAME][:2].tolist() == pytest.approx([1.0, -1.0])
    assert np.isnan(values[FEATURES.FACTOR_NAME][2])
    assert quality[
        f"{FEATURES.FACTOR_NAME}__degenerate_lag_variance_rows"
    ] == 1
    assert quality[
        f"{FEATURES.FACTOR_NAME}__degenerate_lead_variance_rows"
    ] == 1


def test_exact_zero_returns_stay_in_fixed_support() -> None:
    morning = np.zeros(119)
    afternoon = np.zeros(119)
    morning[::7] = np.linspace(-0.02, 0.02, len(morning[::7]))
    afternoon[::11] = np.linspace(0.018, -0.018, len(afternoon[::11]))
    expected = _expected_persistence(morning, afternoon)
    values, eligible, _quality = FEATURES.compute_factor_values(
        closes=_close_path(morning, afternoon)[None, :]
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([expected])


def test_invalid_nonpositive_and_wrong_shapes_fail_closed() -> None:
    returns = np.linspace(-0.01, 0.01, 119)
    valid = _close_path(returns, returns)
    rows = np.vstack((valid, valid, valid))
    rows[0, 10] = np.nan
    rows[1, 20] = 0.0
    rows[2, 30] = -1.0
    values, eligible, quality = FEATURES.compute_factor_values(closes=rows)
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False, False, False]
    assert np.isnan(values[FEATURES.FACTOR_NAME]).all()
    assert quality["invalid_required_close_rows"] == 1
    assert quality[f"{FEATURES.FACTOR_NAME}__nonpositive_close_rows"] == 2
    with pytest.raises(FEATURES.Campaign028FeatureError):
        FEATURES.compute_factor_values(closes=np.ones((1, 239)))


def test_partition_reads_only_close_and_excludes_0930() -> None:
    codes = [570] + list(FEATURES.market.CONTINUOUS_MINUTE_CODES)
    timestamps = [
        pd.Timestamp("2020-01-02") + pd.Timedelta(minutes=int(code))
        for code in codes
    ]
    returns = np.linspace(0.0001, 0.01, 119)
    closes = _close_path(returns, returns)
    raw = pd.DataFrame(
        {
            "datetime": timestamps,
            "symbol": "SH600000",
            "provider": "tushare",
            "close": [-100.0] + closes.tolist(),
        }
    ).loc[:, FEATURES.RAW_COLUMNS]
    base = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2020-01-02")],
            "symbol": ["SH600000"],
        }
    )
    frame, quality = FEATURES.compute_partition_frame(
        raw,
        base,
        None,
        symbol="SH600000",
    )
    assert tuple(frame.columns) == FEATURES.OUTPUT_COLUMNS
    assert frame[f"{FEATURES.FACTOR_NAME}_eligible"].tolist() == [True]
    assert frame[FEATURES.FACTOR_NAME].tolist() == pytest.approx([1.0])
    assert quality["base_rows"] == 1
    assert FEATURES.RAW_COLUMNS == ("datetime", "symbol", "provider", "close")


def test_all_no_return_preregistration_bindings_pass_before_values() -> None:
    records = [
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_028_concept_scouting.json",
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_028_mechanism_overlap_audit.json",
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_028_no_return_preregistration.json",
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_028_preregistration.json",
    ]
    for record in records:
        result = BINDINGS.validate_record(
            record,
            data_root=FEATURES.DEFAULT_DATA_ROOT,
        )
        assert result["all_bindings_passed"] is True
    protocol = FEATURES.load_protocol()
    comparisons = protocol["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 49
    assert comparisons[-1]["name"] == FEATURES.C27_FACTOR_NAMES[0]


def test_walkforward_catalog_is_the_single_frozen_trial() -> None:
    campaign, campaign_sha256 = WALKFORWARD.load_campaign(
        WALKFORWARD.engine_namespace["DEFAULT_CAMPAIGN"]
    )
    assert campaign_sha256 == (
        "99953ff4de553784ede971cf1242c56c02919180dd822c7ba5d7d80e948a320c"
    )
    assert WALKFORWARD.build_trial_catalog(campaign) == [
        {
            "trial_id": (
                "wf028_single__"
                "intraday_absolute_return_serial_persistence_236p"
            ),
            "parent_trial_id": None,
            "kind": "single_factor",
            "feature_set": [FEATURES.FACTOR_NAME],
            "weights": [1.0],
            "complexity": 1,
        }
    ]


def test_research_boundaries_remain_no_return() -> None:
    mechanism = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_028_mechanism_overlap_audit.json"
        ).read_text()
    )
    protocol = FEATURES.load_protocol()
    assert mechanism["research_boundary"]["candidate_values_read"] is False
    assert mechanism["research_boundary"]["comparison_values_read"] is False
    assert mechanism["decision"]["conceptually_independent"] is True
    assert (
        protocol["research_boundary"]["forward_return_fields_read_before_admissibility"]
        is False
    )
    assert FEATURES.engine_namespace["FACTOR_NAME"] == FEATURES.FACTOR_NAME


def test_terminal_record_preserves_closed_stress_and_candidate49() -> None:
    walkforward = (
        REPO_ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_028"
        / "walkforward"
    )
    record_path = (
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_028_research_record.json"
    )
    audit = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/"
            "20260730T072927Z_campaign028_no_return_audit.json"
        ).read_text()
    )
    ledger = json.loads((walkforward / "trial_ledger.json").read_text())
    survivors = json.loads(
        (walkforward / "development_survivors.json").read_text()
    )
    stress = json.loads(
        (walkforward / "exposed_stress_consumption_record.json").read_text()
    )
    record = json.loads(record_path.read_text())
    coverage = audit["coverage_and_capacity"][FEATURES.FACTOR_NAME]
    uniqueness = audit["uniqueness"][FEATURES.FACTOR_NAME]
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["median_coverage"] == pytest.approx(0.9981941305574307)
    assert uniqueness["all_required_comparisons_passed"] is True
    assert len(uniqueness["comparisons"]) == 49
    assert uniqueness[
        "maximum_observed_absolute_median_daily_rank_correlation"
    ] == pytest.approx(0.6849130561345537)
    assert audit["source_fields_read"] == [
        "datetime",
        "symbol",
        "provider",
        "close",
    ]
    assert audit["minute_open_high_low_read"] is False
    assert audit["minute_close_read"] is True
    assert len(ledger["entries"]) == 1
    decision = survivors["trial_decisions"][0]
    assert decision["development_survivor_gate_passed"] is False
    assert decision["positive_mean_rank_ic_fold_count"] == 0
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    assert record["decision"]["factor_terminal"] is True
    assert record["decision"]["candidate49_remains_only_prospective_candidate"] is True
    assert BINDINGS.validate_record(
        record_path,
        data_root=FEATURES.DEFAULT_DATA_ROOT,
    )["all_bindings_passed"] is True


def test_unified_report_contains_campaign028_terminal_result() -> None:
    report = (
        REPO_ROOT
        / "data/experiments/short_horizon/three_day_research_report.md"
    ).read_text()
    assert "## 历史滚动 Campaign028 权威追加" in report
    assert "最大绝对中位日秩相关为 0.684913" in report
    assert "开发期 20bp 累计收益为 -14.01%" in report
