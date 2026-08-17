import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_preregistration_binding_validator as BINDINGS
import scripts.a_share_three_day_walkforward_campaign027_features as FEATURES
import scripts.a_share_three_day_walkforward_campaign027 as WALKFORWARD


REPO_ROOT = Path(__file__).resolve().parents[2]


def _close_path(
    morning_returns: np.ndarray,
    afternoon_returns: np.ndarray,
) -> np.ndarray:
    morning = np.exp(np.r_[0.0, np.cumsum(morning_returns)])
    afternoon = np.exp(np.r_[0.0, np.cumsum(afternoon_returns)])
    return np.r_[morning, afternoon]


def test_profile_persistence_exact_positive_negative_and_degenerate() -> None:
    morning = np.linspace(-0.01, 0.01, FEATURES.RETURNS_PER_HALF)
    closes = np.vstack(
        (
            _close_path(morning, morning),
            _close_path(morning, -morning),
            np.ones(FEATURES.SELECTED_BAR_COUNT),
        )
    )
    values, eligible, quality = FEATURES.compute_factor_values(closes=closes)
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True, False]
    assert values[FEATURES.FACTOR_NAME][:2].tolist() == pytest.approx([1.0, -1.0])
    assert np.isnan(values[FEATURES.FACTOR_NAME][2])
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__degenerate_morning_variance_rows"]
        == 1
    )
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__degenerate_afternoon_variance_rows"]
        == 1
    )


def test_exact_zero_returns_stay_in_fixed_support() -> None:
    morning = np.zeros(FEATURES.RETURNS_PER_HALF)
    morning[::7] = np.linspace(-0.02, 0.02, len(morning[::7]))
    afternoon = morning.copy()
    values, eligible, _quality = FEATURES.compute_factor_values(
        closes=_close_path(morning, afternoon)[None, :]
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([1.0])


def test_invalid_nonpositive_and_wrong_shapes_fail_closed() -> None:
    morning = np.linspace(-0.01, 0.01, FEATURES.RETURNS_PER_HALF)
    valid = _close_path(morning, morning)
    rows = np.vstack((valid, valid, valid))
    rows[0, 10] = np.nan
    rows[1, 20] = 0.0
    rows[2, 30] = -1.0
    values, eligible, quality = FEATURES.compute_factor_values(closes=rows)
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False, False, False]
    assert np.isnan(values[FEATURES.FACTOR_NAME]).all()
    assert quality["invalid_required_close_rows"] == 1
    assert quality[f"{FEATURES.FACTOR_NAME}__nonpositive_close_rows"] == 2
    with pytest.raises(FEATURES.Campaign027FeatureError):
        FEATURES.compute_factor_values(closes=np.ones((1, 239)))


def test_partition_reads_only_close_and_excludes_0930() -> None:
    codes = [570] + list(FEATURES.market.CONTINUOUS_MINUTE_CODES)
    timestamps = [
        pd.Timestamp("2020-01-02") + pd.Timedelta(minutes=int(code))
        for code in codes
    ]
    morning = np.linspace(-0.01, 0.01, FEATURES.RETURNS_PER_HALF)
    closes = _close_path(morning, morning)
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


def test_all_preregistration_bindings_pass_before_values() -> None:
    records = [
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_027_concept_scouting.json",
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_027_mechanism_overlap_audit.json",
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_027_no_return_preregistration.json",
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_027_preregistration.json",
    ]
    for record in records:
        result = BINDINGS.validate_record(record, data_root=FEATURES.DEFAULT_DATA_ROOT)
        assert result["all_bindings_passed"] is True
    protocol = FEATURES.load_protocol()
    comparisons = protocol["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 48
    assert comparisons[-2]["name"] == FEATURES.C25_FACTOR_NAMES[0]
    assert comparisons[-1]["name"] == FEATURES.C26_FACTOR_NAMES[0]


def test_research_boundaries_remain_no_return() -> None:
    mechanism = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_027_mechanism_overlap_audit.json"
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


def test_walkforward_catalog_is_the_single_frozen_trial() -> None:
    campaign, campaign_sha256 = WALKFORWARD.load_campaign(
        WALKFORWARD.engine_namespace["DEFAULT_CAMPAIGN"]
    )
    assert campaign_sha256 == (
        "1024621b6fa15bd96d42033a174dfa7701ed36d05276abb529ad29f7d62a073c"
    )
    assert WALKFORWARD.build_trial_catalog(campaign) == [
        {
            "trial_id": (
                "wf027_single__"
                "intraday_morning_afternoon_return_profile_persistence_119p"
            ),
            "parent_trial_id": None,
            "kind": "single_factor",
            "feature_set": [FEATURES.FACTOR_NAME],
            "weights": [1.0],
            "complexity": 1,
        }
    ]


def test_terminal_record_preserves_close_only_correction_and_closed_stress() -> None:
    audit_path = (
        REPO_ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_027"
        / "no_return/20260730T054919Z_campaign027_no_return_audit.json"
    )
    walkforward = (
        REPO_ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_027"
        / "walkforward"
    )
    correction_path = (
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_027_no_return_semantic_correction_20260730.json"
    )
    record_path = (
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_027_research_record.json"
    )
    audit = json.loads(audit_path.read_text())
    correction = json.loads(correction_path.read_text())
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
    assert coverage["median_coverage"] == pytest.approx(0.9935888543513072)
    assert uniqueness["all_required_comparisons_passed"] is True
    assert len(uniqueness["comparisons"]) == 48
    assert uniqueness[
        "maximum_observed_absolute_median_daily_rank_correlation"
    ] == pytest.approx(0.01191282815156363)
    assert audit["source_fields_read"] == [
        "datetime",
        "symbol",
        "provider",
        "close",
    ]
    assert correction["authoritative_corrected_semantics"][
        "minute_open_high_low_read"
    ] is False
    assert correction["authoritative_corrected_semantics"][
        "minute_close_read"
    ] is True
    assert correction["correction_boundary"]["original_audit_rewritten"] is False
    assert len(ledger["entries"]) == 1
    decision = survivors["trial_decisions"][0]
    assert decision["development_survivor_gate_passed"] is False
    assert decision["positive_mean_rank_ic_fold_count"] == 1
    assert decision["positive_normalized_return_fold_count"] == 0
    assert decision["positive_pilot_return_fold_count"] == 0
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    assert record["decision"]["factor_terminal"] is True
    assert record["decision"]["candidate49_remains_only_prospective_candidate"] is True
    for path in (correction_path, record_path):
        assert BINDINGS.validate_record(
            path,
            data_root=FEATURES.DEFAULT_DATA_ROOT,
        )["all_bindings_passed"] is True


def test_unified_report_contains_campaign027_terminal_result() -> None:
    report = (
        REPO_ROOT
        / "data/experiments/short_horizon/three_day_research_report.md"
    ).read_text()
    assert "## 历史滚动 Campaign027 权威追加" in report
    assert "最大绝对中位日秩相关为 0.011913" in report
    assert "开发期 20bp 累计收益为 -24.25%" in report
    assert "两个字段访问摘要已通过追加记录纠正为 close-only" in report
