import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign022_features as FEATURES
import scripts.a_share_three_day_walkforward_campaign022 as WALKFORWARD


REPO_ROOT = Path(__file__).resolve().parents[2]


def _constant_bars(
    *,
    high: float,
    low: float,
    close: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    shape = (1, FEATURES.SELECTED_BAR_COUNT)
    return (
        np.full(shape, high, dtype=float),
        np.full(shape, low, dtype=float),
        np.full(shape, close, dtype=float),
    )


def test_close_at_high_low_and_geometric_midpoint_hit_exact_scores() -> None:
    high = np.full((3, FEATURES.SELECTED_BAR_COUNT), 4.0)
    low = np.ones_like(high)
    close = np.vstack(
        [
            np.full(FEATURES.SELECTED_BAR_COUNT, 4.0),
            np.ones(FEATURES.SELECTED_BAR_COUNT),
            np.full(FEATURES.SELECTED_BAR_COUNT, 2.0),
        ]
    )
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=high,
        lows=low,
        closes=close,
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True, True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([1.0, -1.0, 0.0])
    assert quality[f"{FEATURES.FACTOR_NAME}__eligible_rows"] == 3


def test_ratio_uses_full_day_summed_log_distances() -> None:
    highs, lows, closes = _constant_bars(high=4.0, low=1.0, close=2.0)
    closes[0, :120] = 4.0
    values, eligible, _ = FEATURES.compute_factor_values(
        highs=highs,
        lows=lows,
        closes=closes,
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([0.5])


def test_zero_range_bars_remain_but_120_positive_ranges_are_required() -> None:
    highs = np.ones((2, FEATURES.SELECTED_BAR_COUNT))
    lows = np.ones_like(highs)
    closes = np.ones_like(highs)
    highs[0, :120] = 2.0
    closes[0, :120] = 2.0
    highs[1, :119] = 2.0
    closes[1, :119] = 2.0
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=highs,
        lows=lows,
        closes=closes,
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, False]
    assert values[FEATURES.FACTOR_NAME][0] == pytest.approx(1.0)
    assert np.isnan(values[FEATURES.FACTOR_NAME][1])
    assert quality[f"{FEATURES.FACTOR_NAME}__zero_range_observations"] == 241
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__insufficient_positive_range_rows"]
        == 1
    )


def test_invalid_shape_nonfinite_nonpositive_and_misordered_fail_closed() -> None:
    with pytest.raises(FEATURES.Campaign022FeatureError):
        FEATURES.compute_factor_values(
            highs=np.ones((1, 239)),
            lows=np.ones((1, 239)),
            closes=np.ones((1, 239)),
        )

    highs = np.full((3, FEATURES.SELECTED_BAR_COUNT), 2.0)
    lows = np.ones_like(highs)
    closes = np.full_like(highs, 1.5)
    closes[0, 3] = np.nan
    lows[1, 4] = 0.0
    closes[2, 5] = 3.0
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=highs,
        lows=lows,
        closes=closes,
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False, False, False]
    assert np.isnan(values[FEATURES.FACTOR_NAME]).all()
    assert quality["invalid_required_high_low_close_rows"] == 1
    assert quality[f"{FEATURES.FACTOR_NAME}__nonpositive_high_low_close_rows"] == 1
    assert quality[f"{FEATURES.FACTOR_NAME}__misordered_high_low_close_rows"] == 1


def test_partition_reads_only_high_low_close_and_excludes_0930() -> None:
    codes = [570] + list(FEATURES.market.CONTINUOUS_MINUTE_CODES)
    timestamps = [
        pd.Timestamp("2020-01-02") + pd.Timedelta(minutes=int(code))
        for code in codes
    ]
    raw = pd.DataFrame(
        {
            "datetime": timestamps,
            "symbol": "SH600000",
            "provider": "tushare",
            "high": [-1.0] + [4.0] * FEATURES.SELECTED_BAR_COUNT,
            "low": [-1.0] + [1.0] * FEATURES.SELECTED_BAR_COUNT,
            "close": [-1.0] + [4.0] * FEATURES.SELECTED_BAR_COUNT,
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
    assert FEATURES.RAW_COLUMNS == (
        "datetime",
        "symbol",
        "provider",
        "high",
        "low",
        "close",
    )


def test_protocol_and_mechanism_are_fingerprint_bound_before_values() -> None:
    concept = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_022_concept_scouting.json"
        ).read_text()
    )
    audit = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_022_mechanism_overlap_audit.json"
        ).read_text()
    )
    protocol = FEATURES.load_protocol()
    assert (
        FEATURES._sha256(FEATURES.CAMPAIGN021_FEATURE_RUNNER)
        == FEATURES.CAMPAIGN021_FEATURE_RUNNER_SHA256
    )
    assert concept["research_boundary"]["candidate_values_read"] is False
    assert audit["selected_mechanism"]["name"] == FEATURES.FACTOR_NAME
    assert audit["selected_mechanism"]["direction"] == "higher"
    assert protocol["candidates"][0]["formula"] == FEATURES.FACTOR_FORMULA
    assert audit["decision"]["conceptually_independent"] is True
    comparisons = protocol["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 43
    assert comparisons[-1]["name"] == FEATURES.C21_FACTOR_NAMES[0]
    assert protocol["finite_post_admissibility_search"][
        "development_trial_count"
    ] == 1


def test_generated_source_records_high_low_close_without_market_benchmark() -> None:
    source = FEATURES._source
    assert '"minute_open_high_low_read_by_status": True' in source
    assert '"minute_open_read_by_status": False' in source
    assert '"minute_close_read_by_status": True' in source
    assert 'value["source_open_high_low_read"] = True' in source
    assert 'value["source_close_read"] = True' in source
    assert 'value["source_volume_read"] = False' in source
    assert "market_benchmark_fields_read" not in source


def test_walkforward_catalog_is_the_single_frozen_trial() -> None:
    campaign, campaign_sha256 = WALKFORWARD.load_campaign(
        WALKFORWARD.engine_namespace["DEFAULT_CAMPAIGN"]
    )
    assert campaign_sha256 == (
        "a9782c89573d655cfd5872cec88cc2a28ff5706750e82f84ccca2d44ea2daf5f"
    )
    assert WALKFORWARD.build_trial_catalog(campaign) == [
        {
            "trial_id": (
                "wf022_single__intraday_intrabar_close_location_pressure_240m"
            ),
            "parent_trial_id": None,
            "kind": "single_factor",
            "feature_set": [FEATURES.FACTOR_NAME],
            "weights": [1.0],
            "complexity": 1,
        }
    ]


def test_terminal_record_and_state_preserve_closed_stress() -> None:
    record = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_022_research_record.json"
        ).read_text()
    )
    state = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_iteration_status_20260729_campaign022.json"
        ).read_text()
    )
    no_return_path = (
        REPO_ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_022"
        / "20260729T065914Z_campaign022_no_return_audit.json"
    )
    no_return = json.loads(no_return_path.read_text())
    ledger = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_022"
            / "walkforward/trial_ledger.json"
        ).read_text()
    )
    survivors = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_022"
            / "walkforward/development_survivors.json"
        ).read_text()
    )
    stress = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_022"
            / "walkforward/exposed_stress_consumption_record.json"
        ).read_text()
    )
    manifest = json.loads(
        (
            FEATURES.output_root(Path("/Volumes/DIsk/qlib-a-share-tushare-1m"))
            / "snapshot_manifest.json"
        ).read_text()
    )
    assert FEATURES._sha256(no_return_path) == FEATURES.NO_RETURN_AUDIT_SHA256
    assert manifest["source_fields_read"] == list(FEATURES.RAW_COLUMNS)
    assert manifest["source_open_high_low_read"] is True
    assert manifest["source_close_read"] is True
    assert manifest["source_volume_read"] is False
    assert manifest["daily_price_fields_read"] == []
    assert manifest["forward_return_fields_read"] is False
    assert manifest["factor_eligible_rows"][FEATURES.FACTOR_NAME] == 6_924_627
    coverage = no_return["coverage_and_capacity"][FEATURES.FACTOR_NAME]
    uniqueness = no_return["uniqueness"][FEATURES.FACTOR_NAME]
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["median_coverage"] == pytest.approx(0.9749496443589075)
    assert coverage["p05_coverage"] == pytest.approx(0.9095754101416853)
    assert uniqueness["all_required_comparisons_passed"] is True
    assert len(uniqueness["comparisons"]) == 43
    assert uniqueness[
        "maximum_observed_absolute_median_daily_rank_correlation"
    ] == pytest.approx(0.6176214397238915)
    assert len(ledger["entries"]) == 1
    decision = survivors["trial_decisions"][0]
    assert decision["development_survivor_gate_passed"] is False
    assert decision["positive_mean_rank_ic_fold_count"] == 1
    assert decision["positive_pilot_return_fold_count"] == 0
    assert survivors["selected_survivor_count"] == 0
    assert survivors["stress_return_fields_read"] is False
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    assert record["decision"]["factor_terminal"] is True
    assert record["development_result"]["development_survivor_count"] == 0
    assert state["research_counts"][
        "recorded_historical_development_trial_count"
    ] == 244
    assert state["active_prospective_candidate"]["signal_ledger"]["entry_count"] == 0
    assert state["active_prospective_candidate"]["execution_ledger"]["entry_count"] == 0
    assert state["decision"][
        "campaign023_concept_scouting_and_separate_no_return_research_allowed"
    ] is True
