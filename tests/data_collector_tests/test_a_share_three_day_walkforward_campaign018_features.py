import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign018_features as FEATURES
import scripts.a_share_three_day_walkforward_campaign018 as WALKFORWARD


REPO_ROOT = Path(__file__).resolve().parents[2]


def _arrays(*, reverse_volume: bool = False) -> tuple[np.ndarray, ...]:
    transformed_ranges = np.linspace(0.0, 0.048, FEATURES.SELECTED_BAR_COUNT)
    log_volumes = np.linspace(0.0, 5.0, FEATURES.SELECTED_BAR_COUNT)
    if reverse_volume:
        log_volumes = log_volumes[::-1]
    center = np.log(100.0)
    highs = np.exp(center + transformed_ranges / 2.0)
    lows = np.exp(center - transformed_ranges / 2.0)
    volumes = np.expm1(log_volumes)
    return highs, lows, volumes


def _compute(
    arrays: tuple[np.ndarray, ...],
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    return FEATURES.compute_factor_values(
        highs=arrays[0].reshape(1, -1),
        lows=arrays[1].reshape(1, -1),
        volumes=arrays[2].reshape(1, -1),
    )


def test_matching_and_opposite_range_volume_profiles_hit_endpoints() -> None:
    positive = _arrays()
    negative = _arrays(reverse_volume=True)
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=np.vstack([positive[0], negative[0]]),
        lows=np.vstack([positive[1], negative[1]]),
        volumes=np.vstack([positive[2], negative[2]]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([1.0, -1.0])
    assert quality[f"{FEATURES.FACTOR_NAME}__eligible_rows"] == 2


def test_exact_zero_range_and_volume_remain_in_fixed_support() -> None:
    arrays = _arrays()
    assert arrays[0][0] == pytest.approx(arrays[1][0])
    assert arrays[2][0] == 0.0
    values, eligible, _ = _compute(arrays)
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([1.0])


def test_zero_range_or_volume_variance_is_missing() -> None:
    highs, lows, volumes = _arrays()
    values, eligible, quality = _compute(
        (np.full_like(highs, 100.0), np.full_like(lows, 100.0), volumes)
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert quality[f"{FEATURES.FACTOR_NAME}__zero_range_variance_rows"] == 1

    values, eligible, quality = _compute(
        (highs, lows, np.zeros_like(volumes))
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert quality[f"{FEATURES.FACTOR_NAME}__zero_volume_variance_rows"] == 1


def test_common_price_scale_does_not_change_factor() -> None:
    arrays = _arrays()
    values, eligible, _ = FEATURES.compute_factor_values(
        highs=np.vstack([arrays[0], arrays[0] * 13.0]),
        lows=np.vstack([arrays[1], arrays[1] * 13.0]),
        volumes=np.vstack([arrays[2], arrays[2]]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True]
    assert values[FEATURES.FACTOR_NAME][0] == pytest.approx(
        values[FEATURES.FACTOR_NAME][1]
    )


def test_invalid_shapes_ordering_prices_volume_and_nonfinite_fail_closed() -> None:
    with pytest.raises(FEATURES.Campaign018FeatureError):
        FEATURES.compute_factor_values(
            highs=np.ones((1, 239)),
            lows=np.ones((1, 239)),
            volumes=np.ones((1, 239)),
        )

    arrays = [array.copy() for array in _arrays()]
    arrays[1][3] = arrays[0][3] + 1.0
    values, eligible, quality = _compute(tuple(arrays))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__low_high_ordering_violation_rows"]
        == 1
    )

    arrays = [array.copy() for array in _arrays()]
    arrays[1][4] = 0.0
    _, eligible, quality = _compute(tuple(arrays))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert quality[f"{FEATURES.FACTOR_NAME}__nonpositive_high_low_rows"] == 1

    arrays = [array.copy() for array in _arrays()]
    arrays[2][5] = -1.0
    _, eligible, quality = _compute(tuple(arrays))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert quality[f"{FEATURES.FACTOR_NAME}__negative_volume_rows"] == 1

    arrays = [array.copy() for array in _arrays()]
    arrays[0][6] = np.nan
    _, eligible, quality = _compute(tuple(arrays))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert quality["invalid_required_high_low_volume_rows"] == 1


def test_partition_reads_only_high_low_volume_and_excludes_0930() -> None:
    arrays = _arrays()
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
            "high": np.concatenate([[-1.0], arrays[0]]),
            "low": np.concatenate([[-1.0], arrays[1]]),
            "volume": np.concatenate([[-1.0], arrays[2]]),
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
        "volume",
    )


def test_concept_audit_parent_and_protocol_are_fingerprint_bound() -> None:
    concept = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_018_concept_scouting.json"
        ).read_text()
    )
    audit = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_018_mechanism_overlap_audit.json"
        ).read_text()
    )
    protocol = FEATURES.load_protocol()
    assert (
        FEATURES._sha256(FEATURES.CAMPAIGN017_FEATURE_RUNNER)
        == FEATURES.CAMPAIGN017_FEATURE_RUNNER_SHA256
    )
    assert concept["selected_concept"]["formula"] is None
    assert concept["selected_concept"]["direction"] is None
    assert concept["research_boundary"]["campaign018_candidate_values_read"] is False
    assert audit["candidate"]["name"] == FEATURES.FACTOR_NAME
    assert audit["candidate"]["formula"] == FEATURES.FACTOR_FORMULA
    assert audit["candidate"]["direction"] == "higher"
    assert audit["candidate"]["selected_bar_count"] == 240
    assert audit["comparison_catalog"]["semantic_registered_mechanism_count"] == 41
    assert audit["comparison_catalog"]["statistical_comparison_factor_count"] == 39
    assert audit["research_boundary"]["forward_return_fields_read"] is False
    comparisons = protocol["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 39
    assert comparisons[-1]["name"] == (
        "intraday_midrange_width_change_coupling_238p"
    )
    assert protocol["finite_post_admissibility_search"][
        "expected_trial_count_if_admitted"
    ] == 1


def test_walkforward_catalog_is_the_single_frozen_trial() -> None:
    campaign, campaign_sha256 = WALKFORWARD.load_campaign(
        WALKFORWARD.engine_namespace["DEFAULT_CAMPAIGN"]
    )
    assert campaign_sha256 == (
        "3b59e6ad5d359a4b12a12280518ec978cf74ed08a4b79c2df3699a4a3a749812"
    )
    assert WALKFORWARD.build_trial_catalog(campaign) == [
        {
            "trial_id": (
                "wf018_single__intraday_range_share_volume_confirmation_240m"
            ),
            "parent_trial_id": None,
            "kind": "single_factor",
            "feature_set": [FEATURES.FACTOR_NAME],
            "weights": [1.0],
            "complexity": 1,
        }
    ]


def test_terminal_record_and_additive_state_preserve_closed_stress() -> None:
    record = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_018_research_record.json"
        ).read_text()
    )
    state = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_iteration_status_20260729_campaign018.json"
        ).read_text()
    )
    no_return = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_018"
            / "no_return/20260729T004232Z_campaign018_no_return_audit.json"
        ).read_text()
    )
    survivors = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_018"
            / "walkforward/development_survivors.json"
        ).read_text()
    )
    stress = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_018"
            / "walkforward/exposed_stress_consumption_record.json"
        ).read_text()
    )
    manifest = json.loads(
        (
            FEATURES.output_root(Path("/Volumes/DIsk/qlib-a-share-tushare-1m"))
            / "snapshot_manifest.json"
        ).read_text()
    )
    assert manifest["source_fields_read"] == list(FEATURES.RAW_COLUMNS)
    assert manifest["source_open_high_low_read"] is True
    assert manifest["source_volume_read"] is True
    assert manifest["source_close_read"] is False
    assert manifest["source_amount_read"] is False
    assert no_return["admissible_factor_names"] == [FEATURES.FACTOR_NAME]
    uniqueness = no_return["uniqueness"][FEATURES.FACTOR_NAME]
    assert uniqueness["all_required_comparisons_passed"] is True
    assert len(uniqueness["comparisons"]) == 39
    assert uniqueness[
        "maximum_observed_absolute_median_daily_rank_correlation"
    ] == pytest.approx(0.6720820650434791)
    assert record["status"] == (
        "completed_zero_development_survivors_stress_interval_not_opened"
    )
    assert record["development_result"]["frozen_trial_count"] == 1
    assert record["development_result"]["operationally_admissible_trial_count"] == 0
    assert record["development_result"]["trial"][
        "development_survivor_gate_passed"
    ] is False
    assert record["development_result"]["trial"][
        "positive_validation_mean_rank_ic_fold_count"
    ] == 0
    assert record["development_result"]["trial"][
        "positive_validation_pilot_10bp_return_fold_count"
    ] == 0
    assert survivors["selected_survivor_count"] == 0
    assert survivors["stress_return_fields_read"] is False
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    assert state["research_counts"][
        "recorded_historical_development_trial_count"
    ] == 241
    assert state["active_prospective_candidate"]["signal_ledger"]["entry_count"] == 0
    assert state["active_prospective_candidate"]["execution_ledger"]["entry_count"] == 0
    assert state["decision"][
        "campaign019_concept_scouting_and_separate_no_return_research_allowed"
    ] is True
